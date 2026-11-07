from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from groq_service import generate_scene_json
from database import create_tables, get_db, Video, SessionLocal, User, PLAN_LIMITS
from tts_service import generate_all_audio, generate_audio_for_scene
from plan_config import (
    PLAN_LANGUAGES, PLAN_HAS_AUDIO, PLAN_DURATIONS,
    estimate_scene_count, get_plan_voices_by_language,
    pick_voice, EDIT_RENDER_LIMITS, EDIT_MAX_SECONDS,
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
import secrets
import hashlib
import hmac
from sqlalchemy import func
import wave
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
        "https://vidora-frontend-three.vercel.app",
    ],
    allow_origin_regex=r"https://vidora-frontend.*\.vercel\.app",
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
class SendOtpRequest(BaseModel):
    name: str
    email: str
    password: str
    turnstile_token: str


class VerifyOtpRequest(BaseModel):
    name: str
    email: str
    password: str
    otp: str


class ResendOtpRequest(BaseModel):
    email: str

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


# ---------------- EMAIL OTP SIGNUP ----------------
# Pending codes live in memory: they reset if the server restarts,
# which is fine because they only live for 10 minutes anyway.
pending_otps: dict = {}
OTP_TTL_SECONDS = 600
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN = 60
OTP_MAX_SENDS = 5
OTP_SALT = os.getenv("SECRET_KEY", "vidora-otp-salt")


def _hash_otp(email: str, otp: str) -> str:
    return hashlib.sha256(f"{email}:{otp}:{OTP_SALT}".encode()).hexdigest()


def _purge_expired_otps():
    now = time.time()
    for key in [k for k, v in pending_otps.items() if now > v["expires_at"]]:
        pending_otps.pop(key, None)


def _find_user_by_email(db: Session, email: str):
    return db.query(User).filter(func.lower(User.email) == email).first()


def verify_turnstile(token: str) -> bool:
    secret = os.getenv("TURNSTILE_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=500, detail="Verification is not configured")
    try:
        r = http_requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": token},
            timeout=10,
        )
        return r.json().get("success") is True
    except Exception as e:
        print("Turnstile error:", e, flush=True)
        return False


def send_otp_email(to_email: str, name: str, otp: str):
    api_key = os.getenv("BREVO_API_KEY")
    sender = os.getenv("BREVO_SENDER_EMAIL")
    if not api_key or not sender:
        raise Exception("Email service is not configured")

    html = (
        f"<div style='font-family:sans-serif;max-width:420px'>"
        f"<h2>Verify your Vidora account</h2>"
        f"<p>Hi {name}, use this code to finish creating your account:</p>"
        f"<p style='font-size:32px;font-weight:800;letter-spacing:6px'>{otp}</p>"
        f"<p>This code expires in 10 minutes. If you didn't request it, ignore this email.</p>"
        f"</div>"
    )
    resp = http_requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": api_key,
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={
            "sender": {"name": "Vidora", "email": sender},
            "to": [{"email": to_email}],
            "subject": "Your Vidora verification code",
            "htmlContent": html,
        },
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        print("Brevo error:", resp.status_code, resp.text, flush=True)
        raise Exception("Could not send verification email")


@app.post("/auth/signup")
def signup_disabled():
    # Signup now requires email verification via /auth/send-otp
    raise HTTPException(
        status_code=410,
        detail="Please sign up using email verification.",
    )


@app.post("/auth/send-otp")
def send_otp(request: SendOtpRequest, db: Session = Depends(get_db)):
    _purge_expired_otps()

    name = request.name.strip()
    email = request.email.strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Please enter your full name")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    if not verify_turnstile(request.turnstile_token):
        raise HTTPException(status_code=400, detail="Verification check failed. Please try again.")

    if _find_user_by_email(db, email):
        raise HTTPException(
            status_code=400,
            detail="This email is already registered. Please log in instead.",
        )

    existing = pending_otps.get(email)
    now = time.time()
    if existing and now - existing["sent_at"] < OTP_RESEND_COOLDOWN:
        wait = int(OTP_RESEND_COOLDOWN - (now - existing["sent_at"]))
        raise HTTPException(status_code=429, detail=f"Please wait {wait}s before requesting another code")

    otp = f"{secrets.randbelow(1000000):06d}"
    pending_otps[email] = {
        "hash": _hash_otp(email, otp),
        "name": name,
        "sent_at": now,
        "expires_at": now + OTP_TTL_SECONDS,
        "attempts": 0,
        "sends": 1,
    }

    try:
        send_otp_email(email, name, otp)
    except Exception as e:
        pending_otps.pop(email, None)
        print("send_otp failed:", e, flush=True)
        raise HTTPException(status_code=500, detail="Could not send the verification email. Please try again.")

    return {"status": "sent"}


@app.post("/auth/resend-otp")
def resend_otp(request: ResendOtpRequest):
    email = request.email.strip().lower()
    entry = pending_otps.get(email)
    if not entry:
        raise HTTPException(status_code=400, detail="Please start signup again")

    now = time.time()
    if now - entry["sent_at"] < OTP_RESEND_COOLDOWN:
        wait = int(OTP_RESEND_COOLDOWN - (now - entry["sent_at"]))
        raise HTTPException(status_code=429, detail=f"Please wait {wait}s before requesting another code")
    if entry["sends"] >= OTP_MAX_SENDS:
        pending_otps.pop(email, None)
        raise HTTPException(status_code=429, detail="Too many codes requested. Please start signup again later.")

    otp = f"{secrets.randbelow(1000000):06d}"
    entry["hash"] = _hash_otp(email, otp)
    entry["sent_at"] = now
    entry["expires_at"] = now + OTP_TTL_SECONDS
    entry["attempts"] = 0
    entry["sends"] += 1

    try:
        send_otp_email(email, entry["name"], otp)
    except Exception as e:
        print("resend_otp failed:", e, flush=True)
        raise HTTPException(status_code=500, detail="Could not send the verification email. Please try again.")

    return {"status": "sent"}


@app.post("/auth/verify-otp")
def verify_otp(request: VerifyOtpRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    name = request.name.strip()
    entry = pending_otps.get(email)

    if not entry:
        raise HTTPException(status_code=400, detail="Code expired or not requested. Please request a new one.")
    if time.time() > entry["expires_at"]:
        pending_otps.pop(email, None)
        raise HTTPException(status_code=400, detail="Code expired. Please request a new one.")
    if entry["attempts"] >= OTP_MAX_ATTEMPTS:
        pending_otps.pop(email, None)
        raise HTTPException(status_code=429, detail="Too many wrong attempts. Please request a new code.")

    entry["attempts"] += 1
    if not hmac.compare_digest(entry["hash"], _hash_otp(email, request.otp.strip())):
        raise HTTPException(status_code=400, detail="Incorrect code. Please check and try again.")

    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if _find_user_by_email(db, email):
        pending_otps.pop(email, None)
        raise HTTPException(status_code=400, detail="This email is already registered. Please log in instead.")

    user = create_user(db, name, email, request.password)
    pending_otps.pop(email, None)

    token = create_access_token({"sub": str(user.id)})
    return {
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email},
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
        render_jobs[job_id]["scenes"] = final_scenes
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
            timeout_seconds = 1800
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
                render_jobs[job_id]["video_db_id"] = video_record.id
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


@app.get("/job-status/{job_id}")
def get_job_status(job_id: str):
    if job_id not in render_jobs:
        return {"error": "Job not found"}
    return {k: v for k, v in render_jobs[job_id].items() if k != "scenes"}


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




## ======================================================================
# VIDEO EDITOR: edit right after generation, Save replaces the video
# ======================================================================
from urllib.parse import urlparse

AUDIO_DIR_ABS = os.path.join(BASE_DIR, "audio_output")
EDIT_MAX_SCENES = 40
EDIT_MIN_FRAMES = 90        # 3 seconds
EDIT_MAX_FRAMES = 3600      # 120 seconds
EDIT_MAX_CLIP_SECONDS = 115
EDIT_MAX_REGENERATIONS = 15
EDIT_CHARACTERS = ("robot", "bulb", "rocket", "owl")
EDIT_POSITIONS = ("right", "left", "top-right", "bottom-right", "bottom-left")
EDIT_MAX_IMAGE_BYTES = 8 * 1024 * 1024
EDIT_MAX_PHOTO_SEARCHES = 100
render_lock = threading.Lock()
photo_allowlist: dict = {}   # job_id -> photo URLs returned by search


def _detect_image_ext(data: bytes):
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


# field name -> (kind, required)
EDIT_SCENE_SCHEMA = {
    "TitleIntro": {"topic": ("str", True)},
    "DefinitionScene": {"term": ("str", True), "explanation": ("str", True)},
    "BulletScene": {"heading": ("str", True), "points": ("list", True)},
    "ComparisonScene": {
        "heading": ("str", True), "leftTitle": ("str", True), "leftPoints": ("list", True),
        "rightTitle": ("str", True), "rightPoints": ("list", True),
    },
    "DiagramScene": {"heading": ("str", True), "steps": ("list", True)},
    "TimelineScene": {"heading": ("str", True), "events": ("events", True)},
    "StatsScene": {
        "label": ("str", False), "number": ("num", True),
        "suffix": ("str", False), "description": ("str", True),
    },
    "IconGridScene": {"heading": ("str", True), "description": ("str", True), "iconNames": ("list", True)},
    "QuoteScene": {"quote": ("str", True), "attribution": ("str", False)},
    "OutroScene": {"summary": ("str", True), "ctaText": ("str", False)},
}
EDIT_DEFAULTS = {
    "label": "Did You Know?",
    "attribution": "Key Takeaway",
    "ctaText": "Watch Next Video",
    "suffix": "",
}


class EditSaveRequest(BaseModel):
    scenes: list


class RegenerateVoiceRequest(BaseModel):
    scene: dict


class UsePhotoRequest(BaseModel):
    url: str


def _clean_text(value, limit=600):
    return str(value if value is not None else "").strip()[:limit]


def _clean_list(value, limit=8):
    if not isinstance(value, list):
        return []
    items = [_clean_text(x, 300) for x in value]
    return [x for x in items if x][:limit]


def _clean_events(value):
    out = []
    if isinstance(value, list):
        for e in value[:8]:
            if isinstance(e, dict):
                year = _clean_text(e.get("year"), 20)
                label = _clean_text(e.get("label"), 200)
                if year or label:
                    out.append({"year": year, "label": label})
    return out


def _clean_number(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or abs(f) > 1e15:
        return None
    return int(f) if f == int(f) else f


def _sanitize_scene_content(raw, index):
    label = f"Slide {index + 1}"
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail=f"{label} is not valid")
    stype = raw.get("type")
    schema = EDIT_SCENE_SCHEMA.get(stype)
    if schema is None:
        raise HTTPException(status_code=400, detail=f"{label} has an unknown type")

    scene = {"type": stype}
    for key, (kind, required) in schema.items():
        value = raw.get(key)
        if kind == "str":
            clean = _clean_text(value) or EDIT_DEFAULTS.get(key, "")
        elif kind == "list":
            clean = _clean_list(value)
        elif kind == "events":
            clean = _clean_events(value)
        else:
            clean = _clean_number(value)
        if required and (clean is None or clean == "" or clean == []):
            raise HTTPException(status_code=400, detail=f"{label}: '{key}' cannot be empty")
        scene[key] = clean
    return scene


def _sanitize_scene(raw, index):
    label = f"Slide {index + 1}"
    scene = _sanitize_scene_content(raw, index)

    # ---- voice ----
    audio_file = raw.get("audio_file") or None
    audio_seconds = 0.0
    if audio_file:
        audio_file = str(audio_file)
        if (
            os.path.basename(audio_file) != audio_file
            or not os.path.exists(os.path.join(AUDIO_DIR_ABS, audio_file))
        ):
            raise HTTPException(
                status_code=400,
                detail=f"{label}: its voice file is missing. Please record it again.",
            )
        try:
            audio_seconds = float(raw.get("audio_seconds") or 0)
        except (TypeError, ValueError):
            audio_seconds = 0.0
        audio_seconds = max(0.0, min(audio_seconds, 300.0))

    # ---- length ----
    try:
        frames = int(raw.get("duration_frames") or 0)
    except (TypeError, ValueError):
        frames = 0
    frames = max(EDIT_MIN_FRAMES, min(frames or 180, EDIT_MAX_FRAMES))
    if audio_file and audio_seconds:
        frames = min(EDIT_MAX_FRAMES, max(frames, int(audio_seconds * 30) + 30))

    # ---- picture ----
    image_file = raw.get("image_file") or None
    if image_file:
        image_file = str(image_file)
        if (
            os.path.basename(image_file) != image_file
            or not image_file.lower().endswith((".jpg", ".png", ".webp"))
            or not os.path.exists(os.path.join(AUDIO_DIR_ABS, image_file))
        ):
            raise HTTPException(
                status_code=400,
                detail=f"{label}: its picture is missing. Please add it again.",
            )

    # ---- character ----
    character = raw.get("character") or None
    if character not in EDIT_CHARACTERS:
        character = None

    def _pos(value, default):
        return value if value in EDIT_POSITIONS else default

    def _size(value, lo, hi, default):
        try:
            n = int(value)
        except (TypeError, ValueError):
            n = default
        return max(lo, min(hi, n))

    scene.update({
        "audio_file": audio_file,
        "audio_seconds": audio_seconds if audio_file else None,
        "duration_frames": frames,
        "duration_seconds": round(frames / 30, 1),
        "image_file": image_file,
        "image_pos": _pos(raw.get("image_pos"), "top-right"),
        "image_size": _size(raw.get("image_size"), 15, 60, 26),
        "character": character,
        "char_pos": _pos(raw.get("char_pos"), "bottom-right"),
        "char_size": _size(raw.get("char_size"), 10, 35, 18),
    })
    return scene


def _get_owned_job(job_id: str, current_user):
    if not current_user:
        raise HTTPException(status_code=401, detail="Please log in again.")
    job = render_jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="This editing session has expired. Please generate the video again.",
        )
    if job.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="This video belongs to another account.")
    if job.get("status") != "done" or not job.get("scenes"):
        raise HTTPException(status_code=409, detail="This video isn't ready to edit yet.")
    return job


@app.get("/edit/{job_id}")
def edit_get(job_id: str, current_user=Depends(get_current_user)):
    job = _get_owned_job(job_id, current_user)
    plan = job.get("plan", "free")
    scenes = []
    for s in job["scenes"]:
        s = dict(s)
        if s.get("audio_file"):
            s["audio_seconds"] = s.get("audio_seconds") or s.get("duration_seconds")
        else:
            s["audio_seconds"] = None
        scenes.append(s)
    return {
        "scenes": scenes,
        "plan": plan,
        "has_audio": PLAN_HAS_AUDIO.get(plan, False),
        "edit_renders_used": job.get("edit_renders_used", 0),
        "edit_renders_limit": EDIT_RENDER_LIMITS.get(plan, 3),
        "max_seconds": EDIT_MAX_SECONDS.get(plan, 300),
    }


@app.post("/edit/{job_id}/upload-voice")
async def edit_upload_voice(
    job_id: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    _get_owned_job(job_id, current_user)
    data = await file.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="That audio file is too large.")

    os.makedirs(AUDIO_DIR_ABS, exist_ok=True)
    filename = f"{job_id}_voice_{uuid.uuid4().hex[:8]}.wav"
    path = os.path.join(AUDIO_DIR_ABS, filename)
    with open(path, "wb") as fh:
        fh.write(data)

    seconds = 0.0
    try:
        with wave.open(path, "rb") as w:
            seconds = w.getnframes() / float(w.getframerate())
    except Exception:
        seconds = 0.0

    if seconds < 0.5 or seconds > EDIT_MAX_CLIP_SECONDS + 1:
        try:
            os.remove(path)
        except OSError:
            pass
        raise HTTPException(
            status_code=400,
            detail=f"Voice clips must be between half a second and {EDIT_MAX_CLIP_SECONDS} seconds.",
        )

    return {"audio_file": filename, "audio_seconds": round(seconds, 2)}


@app.post("/edit/{job_id}/regenerate-voice")
async def edit_regenerate_voice(
    job_id: str,
    request: RegenerateVoiceRequest,
    current_user=Depends(get_current_user),
):
    job = _get_owned_job(job_id, current_user)
    plan = job.get("plan", "free")
    if not PLAN_HAS_AUDIO.get(plan, False):
        raise HTTPException(status_code=403, detail="AI voice is available on the Basic and Premium plans.")
    if job.get("regen_count", 0) >= EDIT_MAX_REGENERATIONS:
        raise HTTPException(status_code=429, detail="You've reached the voice regeneration limit for this video.")

    scene = _sanitize_scene_content(request.scene, 0)
    language = job.get("language") or "english"
    voice = job.get("voice") or pick_voice(plan, language)
    job["regen_count"] = job.get("regen_count", 0) + 1

    try:
        result = await generate_audio_for_scene(
            scene, 0, f"{job_id}_r{uuid.uuid4().hex[:6]}", voice, language
        )
    except Exception as e:
        print("regenerate-voice failed:", e, flush=True)
        raise HTTPException(status_code=500, detail="Could not generate the voice. Please try again.")

    if not result.get("audio_filename"):
        raise HTTPException(status_code=500, detail="Could not generate the voice. Please try again.")

    return {
        "audio_file": result["audio_filename"],
        "audio_seconds": round(result["duration_seconds"], 2),
        "duration_frames": result["duration_frames"],
        "narration": result["narration"],
    }


# ---------------- pictures: upload + Pixabay stock photos ----------------
@app.post("/edit/{job_id}/upload-image")
async def edit_upload_image(
    job_id: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    _get_owned_job(job_id, current_user)
    data = await file.read()
    if len(data) > EDIT_MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="That picture is too large (8 MB max).")
    ext = _detect_image_ext(data)
    if not ext:
        raise HTTPException(status_code=400, detail="Please upload a JPG, PNG or WebP picture.")

    os.makedirs(AUDIO_DIR_ABS, exist_ok=True)
    filename = f"{job_id}_img_{uuid.uuid4().hex[:8]}{ext}"
    with open(os.path.join(AUDIO_DIR_ABS, filename), "wb") as fh:
        fh.write(data)
    return {"image_file": filename}


@app.get("/edit/{job_id}/photos")
def edit_search_photos(job_id: str, q: str, current_user=Depends(get_current_user)):
    job = _get_owned_job(job_id, current_user)
    key = os.getenv("PIXABAY_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Photo search is not set up yet.")
    query = q.strip()[:100]
    if not query:
        raise HTTPException(status_code=400, detail="Type something to search for.")
    if job.get("photo_searches", 0) >= EDIT_MAX_PHOTO_SEARCHES:
        raise HTTPException(status_code=429, detail="You've reached the photo search limit for this video.")
    job["photo_searches"] = job.get("photo_searches", 0) + 1

    try:
        r = http_requests.get(
            "https://pixabay.com/api/",
            params={
                "key": key,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "safesearch": "true",
                "per_page": 12,
            },
            timeout=12,
        )
    except Exception as e:
        print("Pixabay error:", e, flush=True)
        raise HTTPException(status_code=502, detail="Photo search is unavailable right now.")
    if r.status_code != 200:
        print("Pixabay status:", r.status_code, r.text[:200], flush=True)
        raise HTTPException(status_code=502, detail="Photo search is unavailable right now.")

    allowed = photo_allowlist.setdefault(job_id, [])
    photos = []
    for p in r.json().get("hits", []):
        thumb = p.get("webformatURL")
        full = p.get("largeImageURL")
        if thumb and full:
            photos.append({
                "id": p.get("id"),
                "thumb": thumb,
                "url": full,
                "photographer": p.get("user", ""),
                "page": p.get("pageURL", ""),
            })
            allowed.append(full)
    # keep the allow-list small
    if len(allowed) > 300:
        del allowed[: len(allowed) - 300]
    return {"photos": photos}


@app.post("/edit/{job_id}/use-photo")
def edit_use_photo(
    job_id: str,
    request: UsePhotoRequest,
    current_user=Depends(get_current_user),
):
    _get_owned_job(job_id, current_user)

    # Only URLs that our own search returned can be downloaded.
    if not request.url.startswith("https://") or request.url not in photo_allowlist.get(job_id, []):
        raise HTTPException(status_code=400, detail="That photo isn't available. Please search again.")

    try:
        r = http_requests.get(request.url, timeout=20)
    except Exception as e:
        print("photo download error:", e, flush=True)
        raise HTTPException(status_code=502, detail="Could not download that photo.")

    host = urlparse(r.url).hostname or ""
    if not (host == "pixabay.com" or host.endswith(".pixabay.com")):
        raise HTTPException(status_code=502, detail="Could not download that photo.")
    if r.status_code != 200 or len(r.content) > EDIT_MAX_IMAGE_BYTES:
        raise HTTPException(status_code=502, detail="Could not download that photo.")
    ext = _detect_image_ext(r.content)
    if not ext:
        raise HTTPException(status_code=502, detail="That file isn't a usable picture.")

    os.makedirs(AUDIO_DIR_ABS, exist_ok=True)
    filename = f"{job_id}_img_{uuid.uuid4().hex[:8]}{ext}"
    with open(os.path.join(AUDIO_DIR_ABS, filename), "wb") as fh:
        fh.write(r.content)
    return {"image_file": filename}


# ---------------- render + save ----------------
def _remotion_command(output_file: str):
    exe = "remotion.cmd" if os.name == "nt" else "remotion"
    remotion_cmd = os.path.abspath(
        os.path.join(REMOTION_PROJECT_PATH, "node_modules", ".bin", exe)
    )
    if not os.path.exists(remotion_cmd):
        raise Exception("Remotion executable not found on the server")

    base = ["render", "src/index.ts", "FullVideo", output_file, "--overwrite", "--concurrency=1"]
    if os.name == "nt":
        return ["cmd.exe", "/d", "/s", "/c", remotion_cmd] + base
    return [remotion_cmd] + base + [
        "--chromium-flag=--no-sandbox",
        "--chromium-flag=--disable-setuid-sandbox",
        "--chromium-flag=--disable-dev-shm-usage",
        "--chromium-flag=--disable-gpu",
        "--chromium-flag=--use-gl=swiftshader",
    ]


def rerender_job(new_id: str):
    job = render_jobs[new_id]
    scenes = job["scenes"]
    try:
        job["status"] = "queued"
        job["step"] = "Waiting for the render queue"

        with render_lock:
            job["status"] = "processing"
            job["step"] = "Rendering video"

            # voice files -> remotion/public/audio
            os.makedirs(REMOTION_PUBLIC_AUDIO, exist_ok=True)
            for s in scenes:
                f = s.get("audio_file")
                if f:
                    shutil.copy2(
                        os.path.join(AUDIO_DIR_ABS, f),
                        os.path.join(REMOTION_PUBLIC_AUDIO, f),
                    )

            # pictures -> remotion/public/media
            media_dir = os.path.join(REMOTION_PROJECT_PATH, "public", "media")
            os.makedirs(media_dir, exist_ok=True)
            for s in scenes:
                f = s.get("image_file")
                if f:
                    shutil.copy2(
                        os.path.join(AUDIO_DIR_ABS, f),
                        os.path.join(media_dir, f),
                    )

            sample_path = os.path.join(REMOTION_PROJECT_PATH, "src", "sampleScenes.ts")
            with open(sample_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "export const sampleScenes = "
                    + json.dumps(scenes, indent=2, ensure_ascii=False)
                    + ";\n"
                )

            out_dir = os.path.join(REMOTION_PROJECT_PATH, "out")
            os.makedirs(out_dir, exist_ok=True)
            output_filename = f"{new_id}_video.mp4"
            output_file = os.path.abspath(os.path.join(out_dir, output_filename))

            command = _remotion_command(output_file)
            env = os.environ.copy()
            if os.name == "nt":
                for k in ("CHROME_BIN", "PUPPETEER_EXECUTABLE_PATH", "REMOTION_BROWSER_EXECUTABLE"):
                    env.pop(k, None)

            stdout_log = os.path.join(REMOTION_PROJECT_PATH, "remotion_edit_stdout.txt")
            stderr_log = os.path.join(REMOTION_PROJECT_PATH, "remotion_edit_stderr.txt")
            with open(stdout_log, "w", encoding="utf-8", errors="replace") as so, \
                 open(stderr_log, "w", encoding="utf-8", errors="replace") as se:
                process = subprocess.Popen(
                    command,
                    cwd=REMOTION_PROJECT_PATH,
                    env=env,
                    stdout=so,
                    stderr=se,
                    stdin=subprocess.DEVNULL,
                    shell=False,
                )
                try:
                    process.wait(timeout=1800)
                except subprocess.TimeoutExpired:
                    process.kill()
                    raise Exception("The render took too long and was stopped. Try fewer or shorter slides.")

            size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
            if process.returncode != 0 and size < 100000:
                try:
                    with open(stderr_log, "r", encoding="utf-8", errors="replace") as fh:
                        tail = fh.read()[-400:]
                except Exception:
                    tail = ""
                raise Exception("Render failed. " + tail)
            if size < 100000:
                raise Exception("The rendered video came out empty. Please try again.")

            os.makedirs(AUDIO_DIR_ABS, exist_ok=True)
            shutil.copy2(output_file, os.path.join(AUDIO_DIR_ABS, output_filename))

        total_frames = sum(s["duration_frames"] for s in scenes)
        new_url = BASE_URL + "/audio/" + output_filename

        # Replace the saved video in the user's account
        video_db_id = job.get("video_db_id")
        if video_db_id:
            db = SessionLocal()
            try:
                rec = db.query(Video).filter(Video.id == video_db_id).first()
                if rec:
                    rec.video_url = new_url
                    rec.duration_seconds = int(total_frames / 30)
                    rec.scene_count = len(scenes)
                    db.commit()
            finally:
                db.close()

        job["video_url"] = new_url
        job["total_duration_seconds"] = round(total_frames / 30, 1)
        job["step"] = "Finalizing your video"
        job["status"] = "done"

        # Remove the old video file (best effort)
        old_url = job.get("previous_video_url")
        if old_url:
            old_name = os.path.basename(old_url)
            if old_name.endswith(".mp4") and old_name != output_filename:
                try:
                    os.remove(os.path.join(AUDIO_DIR_ABS, old_name))
                except OSError:
                    pass

    except Exception as e:
        print(f"[{new_id}] EDIT RENDER ERROR:", str(e), flush=True)
        job["status"] = "error"
        job["error"] = str(e)


@app.post("/edit/{job_id}/save")
def edit_save(
    job_id: str,
    request: EditSaveRequest,
    current_user=Depends(get_current_user),
):
    job = _get_owned_job(job_id, current_user)
    plan = job.get("plan", "free")

    limit = EDIT_RENDER_LIMITS.get(plan, 3)
    used = job.get("edit_renders_used", 0)
    if used >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"You've used all {limit} edit renders for this video.",
        )

    pending = job.get("edit_job")
    if pending and render_jobs.get(pending, {}).get("status") in ("starting", "queued", "processing"):
        raise HTTPException(status_code=409, detail="An edit is already rendering for this video.")

    raw_scenes = request.scenes
    if not raw_scenes or len(raw_scenes) > EDIT_MAX_SCENES:
        raise HTTPException(status_code=400, detail=f"A video needs between 1 and {EDIT_MAX_SCENES} slides.")

    scenes = [_sanitize_scene(s, i) for i, s in enumerate(raw_scenes)]

    total_frames = sum(s["duration_frames"] for s in scenes)
    max_seconds = EDIT_MAX_SECONDS.get(plan, 300)
    if total_frames > max_seconds * 30:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Your video would be {round(total_frames / 1800, 1)} minutes. "
                f"The limit on your plan is {max_seconds // 60} minutes. Shorten or delete some slides."
            ),
        )

    new_id = str(uuid.uuid4())[:8]
    render_jobs[new_id] = {
        "status": "starting",
        "step": "Waiting for the render queue",
        "video_url": None,
        "error": None,
        "total_duration_seconds": None,
        "user_id": job["user_id"],
        "topic": job.get("topic"),
        "plan": plan,
        "language": job.get("language"),
        "voice": job.get("voice"),
        "duration_minutes": job.get("duration_minutes"),
        "scenes": scenes,
        "edit_renders_used": used + 1,
        "video_db_id": job.get("video_db_id"),
        "previous_video_url": job.get("video_url"),
    }
    job["edit_job"] = new_id

    threading.Thread(target=rerender_job, args=(new_id,), daemon=True).start()

    return {"job_id": new_id, "edit_renders_used": used + 1, "edit_renders_limit": limit}