from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from groq_service import generate_scene_json
from tts_service import generate_all_audio
from database import create_tables, get_db, Video, SessionLocal, User, PLAN_LIMITS
from plan_config import (
    PLAN_LANGUAGES, PLAN_HAS_AUDIO, PLAN_DURATIONS,
    estimate_scene_count, get_plan_voices_by_language,
)
from auth import (
    create_user, authenticate_user, create_access_token,
    decode_token, get_user_by_id, get_user_by_email
)
from pydantic import BaseModel
import fitz
import uuid
import asyncio
import os
import json
import re
import sys
import subprocess
import shutil
import threading
import time
import requests as http_requests
from razorpay_service import (
    get_or_create_customer, create_subscription,
    verify_subscription_signature, verify_webhook_signature,
    cancel_subscription,
)
import json as json_lib
from datetime import datetime
import logging
import os

LOG_FILE = "/tmp/pipeline.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    force=True,
)

logger = logging.getLogger(__name__)
# os.environ["CHROME_BIN"] = "/usr/bin/chromium"
# os.environ["PUPPETEER_EXECUTABLE_PATH"] = "/usr/bin/chromium"
# if os.name != "nt":
#    os.environ["REMOTION_BROWSER_EXECUTABLE"] = "/usr/bin/chromium"
app = FastAPI()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://vidora-frontend-eaxq.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("audio_output", exist_ok=True)
app.mount("/audio", StaticFiles(directory="audio_output"), name="audio")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REMOTION_PROJECT_PATH = os.path.join(BASE_DIR, "remotion-project")
REMOTION_PUBLIC_AUDIO = os.path.join(REMOTION_PROJECT_PATH, "public", "audio")

render_jobs: dict = {}

create_tables()

# --- temporary debug: prints all users to the server log on startup ---
_debug_db = SessionLocal()
print("========== USERS ==========")
print(_debug_db.query(User).all())
print("===========================")
_debug_db.close()

security = HTTPBearer(auto_error=False)


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateSubscriptionRequest(BaseModel):
    plan: str


class VerifySubscriptionRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str
    plan: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    print("========== AUTH ==========")

    if credentials is None:
        print("No credentials")
        return None

    token = credentials.credentials
    print("Token:", token)

    payload = decode_token(token)

    print("Decoded payload:", payload)

    if payload is None:
        print("decode_token() returned None")
        return None

    user_id = payload.get("sub")

    print("User ID:", user_id)

    if user_id is None:
        print("No sub in token")
        return None

    user = db.query(User).filter(User.id == int(user_id)).first()

    print("Database user:", user)

    return user

# NOTE: exposes user id/email/name with no auth check — remove or protect
# this before going live with real users.
@app.get("/debug/users")
def debug_users(db: Session = Depends(get_db)):
    print("DB file:", os.path.abspath("vidora.db"))

    users = db.query(User).all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name
        }
        for u in users
    ]

@app.get("/test123")
async def test123():
    print("TEST123 ENDPOINT HIT", flush=True)
    return {"message": "backend is updated"}

@app.get("/")
def root():
    return {"message": "Vidora backend is running"}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts = []
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]
        text_parts.append(page.get_text())
    pdf_document.close()
    return "\n".join(text_parts).strip()


@app.post("/extract")
async def extract_content(
    file: UploadFile = File(None),
    raw_text: str = Form(None),
):
    if file is not None:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "Only PDF files are supported right now."}
        file_bytes = await file.read()
        extracted_text = extract_text_from_pdf(file_bytes)
        if not extracted_text:
            return {"error": "Could not extract text from this PDF."}
        return {
            "source": "pdf",
            "filename": file.filename,
            "character_count": len(extracted_text),
            "text": extracted_text,
        }
    elif raw_text is not None and raw_text.strip() != "":
        return {
            "source": "text",
            "character_count": len(raw_text),
            "text": raw_text.strip(),
        }
    else:
        return {"error": "Please provide either a PDF file or raw text."}


@app.post("/generate")
async def generate_scenes(
    file: UploadFile = File(None),
    raw_text: str = Form(None),
):
    if file is not None:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "Only PDF files are supported."}
        file_bytes = await file.read()
        extracted_text = extract_text_from_pdf(file_bytes)
        if not extracted_text:
            return {"error": "Could not extract text from this PDF."}
    elif raw_text is not None and raw_text.strip() != "":
        extracted_text = raw_text.strip()
    else:
        return {"error": "Please provide either a PDF file or raw text."}

    try:
        result = generate_scene_json(extracted_text)
        return {
            "status": "success" if result["valid"] else "partial",
            "scene_count": len(result["scenes"]),
            "scenes": result["scenes"],
            "warnings": result["warnings"],
        }
    except Exception as e:
        return {"error": f"Groq generation failed: {str(e)}"}


@app.post("/generate-with-audio")
async def generate_with_audio(
    file: UploadFile = File(None),
    raw_text: str = Form(None),
):
    if file is not None:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "Only PDF files are supported."}
        file_bytes = await file.read()
        extracted_text = extract_text_from_pdf(file_bytes)
        if not extracted_text:
            return {"error": "Could not extract text from this PDF."}
    elif raw_text is not None and raw_text.strip() != "":
        extracted_text = raw_text.strip()
    else:
        return {"error": "Please provide either a PDF file or raw text."}

    try:
        result = generate_scene_json(extracted_text)
        if not result["valid"]:
            return {"error": "Could not generate valid scenes from this content."}
        scenes = result["scenes"]
    except Exception as e:
        return {"error": f"Scene generation failed: {str(e)}"}

    video_id = str(uuid.uuid4())[:8]
    try:
        audio_results = await generate_all_audio(scenes, video_id)
    except Exception as e:
        return {"error": f"Audio generation failed: {str(e)}"}

    final_scenes = []
    for i, scene in enumerate(scenes):
        audio_info = audio_results[i]
        final_scenes.append({
            **scene,
            "audio_file": audio_info.get("audio_filename"),
            "audio_url": BASE_URL + "/audio/" + str(audio_info.get("audio_filename"))
                         if audio_info.get("audio_filename") else None,
            "narration": audio_info.get("narration", ""),
            "duration_seconds": audio_info.get("duration_seconds", 4.0),
            "duration_frames": audio_info.get("duration_frames", 150),
        })

    return {
        "status": "success",
        "video_id": video_id,
        "scene_count": len(final_scenes),
        "scenes": final_scenes,
        "warnings": result.get("warnings", []),
    }


@app.post("/auth/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = create_user(db, request.name, request.email, request.password)
    token = create_access_token({"sub": str(user.id)})
    return {
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email}
    }


@app.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id)})
    return {
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email}
    }


@app.get("/auth/me")
def get_me(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": current_user.id, "name": current_user.name, "email": current_user.email}


@app.get("/my-videos")
def get_my_videos(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    videos = db.query(Video).filter(
        Video.user_id == current_user.id
    ).order_by(Video.created_at.desc()).all()
    return {
        "videos": [
            {
                "id": v.id,
                "topic": v.topic,
                "video_url": v.video_url,
                "duration_seconds": v.duration_seconds,
                "scene_count": v.scene_count,
                "created_at": v.created_at.isoformat(),
            }
            for v in videos
        ]
    }


@app.post("/start-render")
async def start_render(
    file: UploadFile = File(None),
    raw_text: str = Form(None),
    language: str = Form(None),
    voice: str = Form(None),
    duration_minutes: str = Form(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file is not None:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "Only PDF files are supported."}
        file_bytes = await file.read()
        extracted_text = extract_text_from_pdf(file_bytes)
        if not extracted_text:
            return {"error": "Could not extract text from this PDF."}
    elif raw_text is not None and raw_text.strip() != "":
        extracted_text = raw_text.strip()
    else:
        return {"error": "Please provide either a PDF file or raw text."}

    # --- quota check ---
    if current_user:
        if current_user.period_start is None or (datetime.utcnow() - current_user.period_start).days >= 30:
            current_user.videos_used_this_period = 0
            current_user.period_start = datetime.utcnow()
            db.commit()

        limit = PLAN_LIMITS.get(current_user.plan, 1)
        if current_user.videos_used_this_period >= limit:
            return {
                "error": f"You've reached your {current_user.plan} plan limit of {limit} videos this month. Upgrade to generate more."
            }

        current_user.videos_used_this_period += 1
        db.commit()
    else:
        return {"error": "Please log in to generate a video."}

    # --- resolve plan features: language, voice, duration, audio availability ---
    plan = current_user.plan
    allowed_languages = PLAN_LANGUAGES.get(plan, [])
    if PLAN_HAS_AUDIO.get(plan, True):
        resolved_language = (
            language if language in allowed_languages
            else (allowed_languages[0] if allowed_languages else "english")
        )
    else:
        resolved_language = "english"

    voices_by_language = get_plan_voices_by_language(plan)
    allowed_voices = voices_by_language.get(resolved_language, [])
    resolved_voice = voice if voice in allowed_voices else (allowed_voices[0] if allowed_voices else None)

    allowed_durations = PLAN_DURATIONS.get(plan, [3])
    try:
        requested_duration = int(duration_minutes) if duration_minutes else None
    except (TypeError, ValueError):
        requested_duration = None
    resolved_duration = requested_duration if requested_duration in allowed_durations else allowed_durations[0]

    job_id = str(uuid.uuid4())[:8]
    topic_preview = extracted_text[:60] + "..." if len(extracted_text) > 60 else extracted_text

    render_jobs[job_id] = {
        "status": "starting",
        "step": "Reading content",
        "video_url": None,
        "error": None,
        "total_duration_seconds": None,
        "user_id": current_user.id if current_user else None,
        "topic": topic_preview,
        "plan": plan,
        "language": resolved_language,
        "voice": resolved_voice,
        "duration_minutes": resolved_duration,
    }

    def run_pipeline(text: str, jid: str):
        print("THREAD STARTED", flush=True)

        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            print("RUNNING PIPELINE", flush=True)

            loop.run_until_complete(pipeline(text, jid))

            print("PIPELINE FINISHED", flush=True)

        except Exception as e:
            import traceback
            traceback.print_exc()

        finally:
            loop.close()

    thread = threading.Thread(
        target=run_pipeline,
        args=(extracted_text, job_id),
        daemon=True
    )
    thread.start()

    return {
        "job_id": job_id,
        "status": "started",
        "duration_minutes": resolved_duration,
        "language": resolved_language,
        "voice": resolved_voice,
    }


async def pipeline(extracted_text: str, job_id: str):
    try:
        # ============================================================
        # STEP 1: GENERATE SCRIPT / SCENES WITH GROQ
        # ============================================================
        print(f"[{job_id}] Step: Writing script with AI", flush=True)

        render_jobs[job_id]["step"] = "Writing script with AI"
        render_jobs[job_id]["status"] = "processing"

        plan = render_jobs[job_id].get("plan", "premium")
        language = render_jobs[job_id].get("language", "english")
        voice = render_jobs[job_id].get("voice")
        duration_minutes = render_jobs[job_id].get("duration_minutes", 3)

        has_audio = PLAN_HAS_AUDIO.get(plan, True)

        target_scene_count = estimate_scene_count(
            duration_minutes,
            has_audio
        )

        print(
            f"[{job_id}] Duration: {duration_minutes} minutes",
            flush=True
        )

        print(
            f"[{job_id}] Target scenes: {target_scene_count}",
            flush=True
        )

        result = generate_scene_json(
            extracted_text,
            target_scene_count=target_scene_count
        )

        if not result or not result.get("valid"):
            render_jobs[job_id]["status"] = "error"
            render_jobs[job_id]["error"] = (
                "Could not generate valid scenes."
            )
            return

        scenes = result["scenes"]

        print(
            f"[{job_id}] Generated {len(scenes)} scenes",
            flush=True
        )

        # ============================================================
        # STEP 2: GENERATE VOICEOVER
        # ============================================================
        print(
            f"[{job_id}] Step: Generating voiceover",
            flush=True
        )

        render_jobs[job_id]["step"] = "Generating voiceover"

        video_id = job_id

        audio_results = await generate_all_audio(
            scenes,
            video_id,
            plan=plan,
            language=language,
            voice=voice
        )

        print(
            f"[{job_id}] Audio generated for {len(audio_results)} scenes",
            flush=True
        )

        # ============================================================
        # STEP 3: BUILD FINAL SCENE DATA
        # ============================================================
        final_scenes = []
        total_frames = 0

        for i, scene in enumerate(scenes):

            if i >= len(audio_results):
                raise Exception(
                    f"Audio result missing for scene {i + 1}"
                )

            audio_info = audio_results[i]

            duration_frames = audio_info.get(
                "duration_frames",
                150
            )

            total_frames += duration_frames

            audio_filename = audio_info.get(
                "audio_filename"
            )

            final_scenes.append({
                **scene,

                "audio_file": audio_filename,

                "audio_url": (
                    BASE_URL
                    + "/audio/"
                    + str(audio_filename)
                    if audio_filename
                    else None
                ),

                "narration": audio_info.get(
                    "narration",
                    ""
                ),

                "duration_seconds": audio_info.get(
                    "duration_seconds",
                    4.0
                ),

                "duration_frames": duration_frames,
            })

        print(
            f"[{job_id}] Total frames: {total_frames}",
            flush=True
        )

        # ============================================================
        # STEP 4: COPY AUDIO INTO REMOTION PUBLIC FOLDER
        # ============================================================
        os.makedirs(
            REMOTION_PUBLIC_AUDIO,
            exist_ok=True
        )

        audio_source_dir = os.path.join(
            BASE_DIR,
            "audio_output"
        )

        for scene in final_scenes:

            audio_file = scene.get("audio_file")

            if not audio_file:
                continue

            src = os.path.join(
                audio_source_dir,
                audio_file
            )

            dst = os.path.join(
                REMOTION_PUBLIC_AUDIO,
                audio_file
            )

            if os.path.exists(src):

                shutil.copy2(
                    src,
                    dst
                )

                print(
                    f"[{job_id}] Copied audio: {audio_file}",
                    flush=True
                )

            else:

                print(
                    f"[{job_id}] WARNING: Audio not found: {src}",
                    flush=True
                )

        print(
            f"[{job_id}] Audio copied to Remotion public folder",
            flush=True
        )

        # ============================================================
        # STEP 5: UPDATE sampleScenes.ts
        # ============================================================
        sample_scenes_path = os.path.join(
            REMOTION_PROJECT_PATH,
            "src",
            "sampleScenes.ts"
        )

        scenes_json = json.dumps(
            final_scenes,
            indent=2,
            ensure_ascii=False
        )

        sample_scenes_content = (
            "export const sampleScenes = "
            + scenes_json
            + ";\n"
        )

        with open(
            sample_scenes_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(sample_scenes_content)

        print(
            f"[{job_id}] sampleScenes.ts updated",
            flush=True
        )

        # ============================================================
        # STEP 6: PREPARE REMOTION OUTPUT
        # ============================================================
        render_jobs[job_id]["step"] = "Rendering video"

        print(
            f"[{job_id}] Step: Rendering video",
            flush=True
        )

        out_dir = os.path.join(
            REMOTION_PROJECT_PATH,
            "out"
        )

        os.makedirs(
            out_dir,
            exist_ok=True
        )

        output_filename = (
            f"{video_id}_video.mp4"
        )

        output_file = os.path.abspath(
            os.path.join(
                out_dir,
                output_filename
            )
        )

        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except PermissionError:
                print(
                    f"[{job_id}] Existing output file is locked. "
                    f"Waiting before continuing...",
                    flush=True
                )
                await asyncio.sleep(2)

                if os.path.exists(output_file):
                    raise Exception(
                        f"Output file is locked: {output_file}"
                    )

        print(
            f"[{job_id}] Output file: {output_file}",
            flush=True
        )

        # ============================================================
        # STEP 7: FIND REMOTION EXECUTABLE
        # ============================================================
        if os.name == "nt":

            remotion_cmd = os.path.join(
                REMOTION_PROJECT_PATH,
                "node_modules",
                ".bin",
                "remotion.cmd"
            )

        else:

            remotion_cmd = os.path.join(
                REMOTION_PROJECT_PATH,
                "node_modules",
                ".bin",
                "remotion"
            )

        remotion_cmd = os.path.abspath(
            remotion_cmd
        )

        if not os.path.exists(remotion_cmd):

            raise Exception(
                f"Remotion executable not found: "
                f"{remotion_cmd}"
            )

        print(
            f"[{job_id}] Remotion executable found: "
            f"{remotion_cmd}",
            flush=True
        )

        # ============================================================
        # STEP 8: BUILD REMOTION COMMAND
        # ============================================================
        if os.name == "nt":

            command = [
                "cmd.exe",
                "/d",
                "/s",
                "/c",
                remotion_cmd,
                "render",
                "src/index.ts",
                "FullVideo",
                output_file,
                "--overwrite",
                "--log=verbose",
                "--concurrency=1",
            ]

        else:

            command = [
                remotion_cmd,
                "render",
                "src/index.ts",
                "FullVideo",
                output_file,
                "--overwrite",
                "--log=verbose",
                "--concurrency=1",
            ]

        # ============================================================
        # STEP 9: PREPARE ENVIRONMENT
        # ============================================================
        env = os.environ.copy()

        if os.name != "nt":
            command += [
               "--chromium-flag=--no-sandbox",
               "--chromium-flag=--disable-setuid-sandbox",
               "--chromium-flag=--disable-dev-shm-usage",
               "--chromium-flag=--disable-gpu",
               "--chromium-flag=--use-gl=swiftshader",
            ]

        else:

            env.pop(
                "CHROME_BIN",
                None
            )

            env.pop(
                "PUPPETEER_EXECUTABLE_PATH",
                None
            )

            env.pop(
                "REMOTION_BROWSER_EXECUTABLE",
                None
            )

        # ============================================================
        # STEP 10: DEBUG INFORMATION
        # ============================================================
        print(
            "========== REMOTION DEBUG ==========",
            flush=True
        )

        print(
            "Operating system:",
            os.name,
            flush=True
        )

        print(
            "Python:",
            sys.executable,
            flush=True
        )

        print(
            "Node:",
            shutil.which("node"),
            flush=True
        )

        print(
            "NPM:",
            shutil.which("npm"),
            flush=True
        )

        print(
            "NPX:",
            shutil.which("npx"),
            flush=True
        )

        print(
            "Remotion:",
            remotion_cmd,
            flush=True
        )

        print(
            "Remotion exists:",
            os.path.exists(remotion_cmd),
            flush=True
        )

        print(
            "Working directory:",
            REMOTION_PROJECT_PATH,
            flush=True
        )

        print(
            "Output:",
            output_file,
            flush=True
        )

        print(
            "Command:",
            command,
            flush=True
        )

        print(
            "====================================",
            flush=True
        )

        # ============================================================
        # STEP 11: RUN REMOTION
        # ============================================================
        print(
            f"[{job_id}] ABOUT TO RUN REMOTION",
            flush=True
        )

        stdout_log = os.path.join(
            REMOTION_PROJECT_PATH,
            "remotion_stdout.txt"
        )

        stderr_log = os.path.join(
            REMOTION_PROJECT_PATH,
            "remotion_stderr.txt"
        )

        # Open logs so Remotion output is written continuously.
        with open(
            stdout_log,
            "w",
            encoding="utf-8",
            errors="replace"
        ) as stdout_file, open(
            stderr_log,
            "w",
            encoding="utf-8",
            errors="replace"
        ) as stderr_file:

            process = subprocess.Popen(
                command,
                cwd=REMOTION_PROJECT_PATH,
                env=env,
                stdout=stdout_file,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL,
                shell=False,
            )

            print(
                f"[{job_id}] Remotion PID: "
                f"{process.pid}",
                flush=True
            )

            # --------------------------------------------------------
            # Wait for Remotion while periodically checking the output.
            # --------------------------------------------------------
            timeout_seconds = 900
            start_time = time.time()

            while True:

                return_code = process.poll()

                if return_code is not None:
                    break

                elapsed = time.time() - start_time

                # Show progress every 10 seconds.
                if int(elapsed) % 10 == 0:

                    if os.path.exists(output_file):

                        try:
                            file_size = os.path.getsize(
                                output_file
                            )

                            print(
                                f"[{job_id}] Rendering... "
                                f"{int(elapsed)}s | "
                                f"Current MP4 size: "
                                f"{file_size:,} bytes",
                                flush=True
                            )

                        except OSError:
                            pass

                    else:

                        print(
                            f"[{job_id}] Rendering... "
                            f"{int(elapsed)}s | "
                            f"MP4 not created yet",
                            flush=True
                        )

                    await asyncio.sleep(1)

                else:
                    await asyncio.sleep(1)

                if elapsed > timeout_seconds:

                    print(
                        f"[{job_id}] Remotion exceeded "
                        f"{timeout_seconds} seconds.",
                        flush=True
                    )

                    try:
                        process.kill()
                    except Exception:
                        pass

                    raise Exception(
                        "Remotion render timed out after "
                        "15 minutes."
                    )

        # ============================================================
        # STEP 12: REMOTION FINISHED
        # ============================================================
        print(
            f"[{job_id}] REMOTION PROCESS FINISHED",
            flush=True
        )

        print(
            f"[{job_id}] REMOTION RETURN CODE: "
            f"{process.returncode}",
            flush=True
        )

        # Read the logs after the process has finished.
        try:

            with open(
                stdout_log,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as f:

                remotion_stdout = f.read()

        except Exception:

            remotion_stdout = ""

        try:

            with open(
                stderr_log,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as f:

                remotion_stderr = f.read()

        except Exception:

            remotion_stderr = ""

        print(
            "========== REMOTION STDOUT ==========",
            flush=True
        )

        print(
            remotion_stdout[-10000:],
            flush=True
        )

        print(
            "========== REMOTION STDERR ==========",
            flush=True
        )

        print(
            remotion_stderr[-10000:],
            flush=True
        )

        # ============================================================
        # STEP 13: CHECK RENDER RESULT
        # ============================================================
        output_exists = os.path.exists(
            output_file
        )

        output_size = (
            os.path.getsize(output_file)
            if output_exists
            else 0
        )

        print(
            f"[{job_id}] OUTPUT EXISTS: "
            f"{output_exists}",
            flush=True
        )

        print(
            f"[{job_id}] OUTPUT SIZE: "
            f"{output_size:,} bytes",
            flush=True
        )

        print(
            f"[{job_id}] OUTPUT PATH: "
            f"{output_file}",
            flush=True
        )

        # If Remotion failed AND no valid output exists,
        # report the actual Remotion error.
        if process.returncode != 0:

            if output_exists and output_size > 100000:

                print(
                    f"[{job_id}] Remotion returned "
                    f"{process.returncode}, but a valid "
                    f"MP4 exists. Continuing.",
                    flush=True
                )

            else:

                error_message = (
                    "Remotion render failed."
                )

                if remotion_stderr:
                    error_message += (
                        "\n\n"
                        + remotion_stderr[-5000:]
                    )

                elif remotion_stdout:
                    error_message += (
                        "\n\n"
                        + remotion_stdout[-5000:]
                    )

                raise Exception(
                    error_message
                )

        if not output_exists:

            raise Exception(
                "Remotion completed but the MP4 "
                "file was not created:\n"
                + output_file
            )

        if output_size < 100000:

            raise Exception(
                "Remotion produced an MP4 file, "
                "but the file is unexpectedly small: "
                f"{output_size} bytes"
            )

        # ============================================================
        # STEP 14: COPY VIDEO TO SERVED DIRECTORY
        # ============================================================
        serve_dir = os.path.join(
            BASE_DIR,
            "audio_output"
        )

        os.makedirs(
            serve_dir,
            exist_ok=True
        )

        serve_path = os.path.join(
            serve_dir,
            output_filename
        )

        shutil.copy2(
            output_file,
            serve_path
        )

        print(
            f"[{job_id}] Video copied to:",
            serve_path,
            flush=True
        )

        # ============================================================
        # STEP 15: FINALIZE JOB
        # ============================================================
        render_jobs[job_id]["status"] = "done"

        render_jobs[job_id]["step"] = (
            "Finalizing your video"
        )

        render_jobs[job_id]["video_url"] = (
            BASE_URL
            + "/audio/"
            + output_filename
        )

        render_jobs[job_id]["total_duration_seconds"] = (
            round(
                total_frames / 30,
                1
            )
        )

        print(
            f"[{job_id}] VIDEO READY: "
            f"{render_jobs[job_id]['video_url']}",
            flush=True
        )

        # ============================================================
        # STEP 16: SAVE VIDEO TO DATABASE
        # ============================================================
        user_id = render_jobs[job_id].get(
            "user_id"
        )

        topic = render_jobs[job_id].get(
            "topic",
            "Educational Video"
        )

        if user_id:

            try:

                db = SessionLocal()

                video_record = Video(
                    user_id=user_id,
                    topic=topic,
                    video_url=(
                        BASE_URL
                        + "/audio/"
                        + output_filename
                    ),
                    duration_seconds=int(
                        total_frames / 30
                    ),
                    scene_count=len(
                        final_scenes
                    ),
                )

                db.add(video_record)

                db.commit()

                db.close()

                print(
                    f"[{job_id}] Video saved to database "
                    f"for user {user_id}",
                    flush=True
                )

            except Exception as db_err:

                print(
                    f"[{job_id}] Failed to save video "
                    f"to DB: {db_err}",
                    flush=True
                )

    # ================================================================
    # PIPELINE ERROR HANDLER
    # ================================================================
    except Exception as e:

        print(
            f"[{job_id}] PIPELINE EXCEPTION:",
            str(e),
            flush=True
        )

        render_jobs[job_id]["status"] = "error"

        render_jobs[job_id]["step"] = (
            render_jobs[job_id].get(
                "step",
                "Processing"
            )
        )

        render_jobs[job_id]["error"] = str(e)
@app.post("/auth/google")
async def google_auth(
    request: dict,
    db: Session = Depends(get_db)
):
    credential = request.get("credential")
    if not credential:
        raise HTTPException(status_code=400, detail="No credential provided")

    google_url = "https://oauth2.googleapis.com/tokeninfo?id_token=" + credential
    response = http_requests.get(google_url)

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_data = response.json()

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if google_data.get("aud") != client_id:
        raise HTTPException(status_code=401, detail="Token not intended for this app")

    google_email = google_data.get("email")
    google_name = google_data.get("name", google_email)

    if not google_email:
        raise HTTPException(status_code=400, detail="Could not get email from Google")

    existing_user = get_user_by_email(db, google_email)
    if existing_user:
        user = existing_user
    else:
        random_password = str(uuid.uuid4())
        user = create_user(db, google_name, google_email, random_password)

    token = create_access_token({"sub": str(user.id)})

    return {
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        }
    }


@app.get("/job-status/{job_id}")
def get_job_status(job_id: str):
    if job_id not in render_jobs:
        return {"error": "Job not found"}
    return render_jobs[job_id]


@app.post("/billing/create-subscription")
def create_subscription_endpoint(
    request: CreateSubscriptionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if request.plan not in ("basic", "premium"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    if not current_user.razorpay_customer_id:
        try:
            customer_id = get_or_create_customer(
                current_user.name,
                current_user.email,
            )
            current_user.razorpay_customer_id = customer_id
            db.commit()
        except Exception as e:
            print("RAZORPAY ERROR:", str(e))
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    subscription = create_subscription(request.plan, current_user.razorpay_customer_id)

    current_user.razorpay_subscription_id = subscription["id"]
    current_user.subscription_status = "created"
    db.commit()

    return {
        "subscription_id": subscription["id"],
        "razorpay_key_id": os.getenv("RAZORPAY_KEY_ID"),
        "plan": request.plan,
    }


@app.post("/billing/verify-subscription")
def verify_subscription_endpoint(
    request: VerifySubscriptionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    is_valid = verify_subscription_signature(
        request.razorpay_subscription_id,
        request.razorpay_payment_id,
        request.razorpay_signature,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    if request.plan not in ("basic", "premium"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    current_user.plan = request.plan
    current_user.subscription_status = "active"
    current_user.videos_used_this_period = 0
    current_user.period_start = datetime.utcnow()
    db.commit()

    return {"status": "success", "plan": current_user.plan}


@app.post("/billing/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json_lib.loads(body)
    event_type = event.get("event")
    payload = event.get("payload", {})

    subscription_entity = payload.get("subscription", {}).get("entity", {})
    subscription_id = subscription_entity.get("id")

    if not subscription_id:
        return {"status": "ignored"}

    user = db.query(User).filter(
        User.razorpay_subscription_id == subscription_id
    ).first()
    if not user:
        return {"status": "user_not_found"}

    if event_type == "subscription.activated":
        notes = subscription_entity.get("notes", {})
        plan_key = notes.get("vidora_plan", "basic")
        user.plan = plan_key
        user.subscription_status = "active"
        user.videos_used_this_period = 0
        user.period_start = datetime.utcnow()

    elif event_type == "subscription.charged":
        user.videos_used_this_period = 0
        user.period_start = datetime.utcnow()
        user.subscription_status = "active"

    elif event_type in ("subscription.cancelled", "subscription.halted", "subscription.expired"):
        user.plan = "free"
        user.subscription_status = "cancelled"
        user.razorpay_subscription_id = None

    db.commit()
    return {"status": "processed"}


@app.get("/billing/status")
def billing_status(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    limit = PLAN_LIMITS.get(current_user.plan, 1)

    return {
        "plan": current_user.plan,
        "subscription_status": current_user.subscription_status,
        "videos_used": current_user.videos_used_this_period,
        "videos_limit": limit,
        "period_start": current_user.period_start.isoformat() if current_user.period_start else None,
        "has_audio": PLAN_HAS_AUDIO.get(current_user.plan, True),
        "languages": PLAN_LANGUAGES.get(current_user.plan, []),
        "durations": PLAN_DURATIONS.get(current_user.plan, [3]),
        "voices_by_language": get_plan_voices_by_language(current_user.plan),
    }