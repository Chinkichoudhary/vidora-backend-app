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
import os
import json
import re
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

os.environ["CHROME_BIN"] = "/usr/bin/chromium"
os.environ["PUPPETEER_EXECUTABLE_PATH"] = "/usr/bin/chromium"
os.environ["REMOTION_BROWSER_EXECUTABLE"] = "/usr/bin/chromium"

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
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(pipeline(text, jid))
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
        print(f"[{job_id}] Step: Writing script with AI")
        render_jobs[job_id]["step"] = "Writing script with AI"
        render_jobs[job_id]["status"] = "processing"

        plan = render_jobs[job_id].get("plan", "premium")
        language = render_jobs[job_id].get("language", "english")
        voice = render_jobs[job_id].get("voice")
        #duration_minutes = render_jobs[job_id].get("duration_minutes", 3)
        duration_minutes = 0.1
        has_audio = PLAN_HAS_AUDIO.get(plan, True)
        target_scene_count = estimate_scene_count(duration_minutes, has_audio)

        result = generate_scene_json(extracted_text, target_scene_count=target_scene_count)
        if not result["valid"]:
            render_jobs[job_id]["status"] = "error"
            render_jobs[job_id]["error"] = "Could not generate valid scenes."
            return
        scenes = result["scenes"]
        print(f"[{job_id}] Generated {len(scenes)} scenes (target was {target_scene_count})")

        print(f"[{job_id}] Step: Generating voiceover")
        render_jobs[job_id]["step"] = "Generating voiceover"
        video_id = job_id
        audio_results = await generate_all_audio(scenes, video_id, plan=plan, language=language, voice=voice)
        print(f"[{job_id}] Audio generated for {len(audio_results)} scenes")

        final_scenes = []
        total_frames = 0
        for i, scene in enumerate(scenes):
            audio_info = audio_results[i]
            duration_frames = audio_info.get("duration_frames", 150)
            total_frames += duration_frames
            final_scenes.append({
                **scene,
                "audio_file": audio_info.get("audio_filename"),
                "audio_url": BASE_URL + "/audio/" + str(audio_info.get("audio_filename"))
                             if audio_info.get("audio_filename") else None,
                "narration": audio_info.get("narration", ""),
                "duration_seconds": audio_info.get("duration_seconds", 4.0),
                "duration_frames": duration_frames,
            })

        print(f"[{job_id}] Total frames: {total_frames}")

        os.makedirs(REMOTION_PUBLIC_AUDIO, exist_ok=True)
        for scene in final_scenes:
            if scene.get("audio_file"):
                src = os.path.join("audio_output", scene["audio_file"])
                dst = os.path.join(REMOTION_PUBLIC_AUDIO, scene["audio_file"])
                if os.path.exists(src):
                    shutil.copy(src, dst)

        print(f"[{job_id}] Audio copied to Remotion public folder")

        sample_scenes_path = os.path.join(
            REMOTION_PROJECT_PATH, "src", "sampleScenes.ts"
        )
        scenes_json = json.dumps(final_scenes, indent=2)
        sample_scenes_content = "export const sampleScenes = " + scenes_json + ";\n"
        with open(sample_scenes_path, "w", encoding="utf-8") as f:
            f.write(sample_scenes_content)

        print(f"[{job_id}] sampleScenes.ts updated")

        root_path = os.path.join(REMOTION_PROJECT_PATH, "src", "Root.tsx")
        with open(root_path, "r", encoding="utf-8") as f:
            root_content = f.read()
        root_content = re.sub(
            r'(id="FullVideo"[^<]*?)durationInFrames=\{\d+\}',
            r'\1durationInFrames={' + str(total_frames) + r'}',
            root_content,
            flags=re.DOTALL
        )
        with open(root_path, "w", encoding="utf-8") as f:
            f.write(root_content)

        print(f"[{job_id}] Root.tsx updated")
        print(f"[{job_id}] Step: Rendering video")
        render_jobs[job_id]["step"] = "Rendering video"

        output_filename = video_id + "_video.mp4"
        output_path = os.path.join(REMOTION_PROJECT_PATH, "out", output_filename)
        os.makedirs(os.path.join(REMOTION_PROJECT_PATH, "out"), exist_ok=True)

        time.sleep(3)

        print(f"[{job_id}] Starting Remotion render subprocess...")
        print(f"[{job_id}] Output path: {output_path}")

        duration_minutes_for_timeout = render_jobs[job_id].get("duration_minutes", 3)
        render_timeout = max(1800, int(duration_minutes_for_timeout) * 300)
        print(f"[{job_id}] Render timeout set to {render_timeout}s for a {duration_minutes_for_timeout}-minute video")

        try:
            print(f"[{job_id}] About to start Remotion")

            command = [
    "npx",
    "remotion",
    "render",
    "FullVideo",
    output_path,
    "--concurrency=1",
    "--image-format=jpeg",
    "--log=verbose",
    "--chromium-flag=--no-sandbox",
    "--chromium-flag=--disable-setuid-sandbox",
    "--chromium-flag=--disable-dev-shm-usage",
    "--chromium-flag=--disable-gpu",
    "--chromium-flag=--disable-software-rasterizer",
    "--chromium-flag=--disable-features=VizDisplayCompositor",
    "--chromium-flag=--use-gl=swiftshader",
]
            

            env = os.environ.copy()
            #env["CHROME_BIN"] = "/usr/bin/chromium"
            #env["PUPPETEER_EXECUTABLE_PATH"] = "/usr/bin/chromium"
            #env["REMOTION_BROWSER_EXECUTABLE"] = "/usr/bin/chromium"

            print("========== COMMAND ==========") 
            print(" ".join(command))
            import subprocess

            print("========== MEMORY ==========")
            subprocess.run("free -h", shell=True)

            print("========== DISK ==========")
            subprocess.run("df -h", shell=True)
            render_result = subprocess.run(
                command,
                cwd=REMOTION_PROJECT_PATH,
                env=env,
                capture_output=True,
                text=True,
                timeout=render_timeout,
                #shell = True,
            )
          

            print(f"[{job_id}] subprocess.run() returned")

            print("========== STDOUT ==========")
            print(render_result.stdout)

            print("========== STDERR ==========")
            print(render_result.stderr)

            print(f"[{job_id}] Return code = {render_result.returncode}")

        except subprocess.TimeoutExpired:
            print(f"[{job_id}] RENDER TIMED OUT")
            render_jobs[job_id]["status"] = "error"
            render_jobs[job_id]["error"] = f"Render timed out after {render_timeout // 60} minutes"
            return

        except Exception as render_err:
            print(f"[{job_id}] RENDER EXCEPTION: {str(render_err)}")
            render_jobs[job_id]["status"] = "error"
            render_jobs[job_id]["error"] = "Render subprocess failed: " + str(render_err)
            return

        if render_result.returncode != 0:
            render_jobs[job_id]["status"] = "error"
            render_jobs[job_id]["error"] = render_result.stderr[-1000:]
            return

        if not os.path.exists(output_path):
            print(f"[{job_id}] ERROR: Output file does not exist after render")
            render_jobs[job_id]["status"] = "error"
            render_jobs[job_id]["error"] = "Render completed but output file was not created."
            return

        serve_path = os.path.join("audio_output", output_filename)
        shutil.copy(output_path, serve_path)

        print(f"[{job_id}] DONE - Video ready at {serve_path}")

        render_jobs[job_id]["status"] = "done"
        render_jobs[job_id]["step"] = "Finalizing your video"
        render_jobs[job_id]["video_url"] = BASE_URL + "/audio/" + output_filename
        render_jobs[job_id]["total_duration_seconds"] = round(total_frames / 30, 1)

        user_id = render_jobs[job_id].get("user_id")
        topic = render_jobs[job_id].get("topic", "Educational Video")
        if user_id:
            try:
                db = SessionLocal()
                video_record = Video(
                    user_id=user_id,
                    topic=topic,
                    video_url=BASE_URL + "/audio/" + output_filename,
                    duration_seconds=int(total_frames / 30),
                    scene_count=len(final_scenes),
                )
                db.add(video_record)
                db.commit()
                db.close()
                print(f"[{job_id}] Video saved to database for user {user_id}")
            except Exception as db_err:
                print(f"[{job_id}] Failed to save video to DB: {str(db_err)}")

    except Exception as e:
        print(f"[{job_id}] PIPELINE EXCEPTION: {str(e)}")
        render_jobs[job_id]["status"] = "error"
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