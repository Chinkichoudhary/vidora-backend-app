"""
tts_service.py
Generates voiceover audio for each scene using Microsoft Edge TTS.
Completely free — no API key needed.
Supports multiple languages and voices based on the user's subscription plan.
"""

import edge_tts
import asyncio
import os

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing from .env")

groq_client = Groq(api_key=GROQ_API_KEY)
from plan_config import PLAN_HAS_AUDIO, SCENE_DURATIONS_NO_AUDIO, pick_voice, get_voices_for_language
AUDIO_DIR = "audio_output"

LANGUAGE_NAMES = {
    "english": "English",
    "hindi": "Hindi",
    "spanish": "Spanish",
    "french": "French",
    "german": "German",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "japanese": "Japanese",
}


def ensure_audio_dir():
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)


async def scene_to_narration(scene: dict, language: str = "english") -> str:
    """
    Calls Groq to generate a rich teacher-style explanation for each scene,
    written entirely in the given language.
    """
   
    scene_type = scene.get("type", "")
    target_language = LANGUAGE_NAMES.get(language, "English")

    if scene_type == "TitleIntro":
        instruction = (
            f"You are introducing a video about '{scene.get('topic', '')}'. "
            f"Welcome the viewer warmly, tell them what they will learn, "
            f"why this topic is important and interesting, and get them excited. "
            f"Speak like an enthusiastic teacher. 3-4 sentences."
        )

    elif scene_type == "DefinitionScene":
        term = scene.get("term", "")
        explanation = scene.get("explanation", "")
        instruction = (
            f"The screen shows the definition of '{term}': {explanation}. "
            f"Explain this term to a student in a conversational way. "
            f"Give a real-life example or analogy to make it easy to understand. "
            f"Tell them why this term matters. 4-5 sentences."
        )

    elif scene_type == "BulletScene":
        heading = scene.get("heading", "")
        points_text = ", ".join(scene.get("points", []))
        instruction = (
            f"The screen shows bullet points about '{heading}': {points_text}. "
            f"Explain each point like a teacher — don't just read them. "
            f"For each point, add a brief example or why it matters. "
            f"Make it conversational and educational. 5-7 sentences."
        )

    elif scene_type == "ComparisonScene":
        heading = scene.get("heading", "")
        left_title = scene.get("leftTitle", "")
        left_points = ", ".join(scene.get("leftPoints", []))
        right_title = scene.get("rightTitle", "")
        right_points = ", ".join(scene.get("rightPoints", []))
        instruction = (
            f"The screen compares {left_title} ({left_points}) "
            f"vs {right_title} ({right_points}). "
            f"Explain the key differences like a teacher. "
            f"Give a real-life example that makes the difference clear. "
            f"Tell students which exam questions commonly test this. 5-6 sentences."
        )

    elif scene_type == "DiagramScene":
        heading = scene.get("heading", "")
        steps = ", ".join(scene.get("steps", []))
        instruction = (
            f"The screen shows a step-by-step process: '{heading}' with steps: {steps}. "
            f"Walk through each step conversationally like a teacher. "
            f"Explain what happens at each step and why it leads to the next. "
            f"Use a simple real-world analogy to make the process memorable. 5-7 sentences."
        )

    elif scene_type == "TimelineScene":
        heading = scene.get("heading", "")
        events = scene.get("events", [])
        events_text = ", ".join([f"{e.get('year')}: {e.get('label')}" for e in events])
        instruction = (
            f"The screen shows a timeline of '{heading}': {events_text}. "
            f"Narrate the timeline like a storyteller — explain why each event was significant. "
            f"Connect the events to show how one led to the next. "
            f"Make history feel exciting and relevant. 5-6 sentences."
        )

    elif scene_type == "StatsScene":
        number = scene.get("number", "")
        suffix = scene.get("suffix", "")
        description = scene.get("description", "")
        instruction = (
            f"The screen shows an amazing statistic: {number} {suffix} — {description}. "
            f"React to this number with genuine amazement. "
            f"Give 2 creative real-world comparisons to help the viewer truly grasp how big this number is. "
            f"Make it memorable and mind-blowing. 4-5 sentences."
        )

    elif scene_type == "IconGridScene":
        heading = scene.get("heading", "")
        description = scene.get("description", "")
        instruction = (
            f"The screen shows a grid of concepts about '{heading}': {description}. "
            f"Explain how all these concepts connect to each other. "
            f"Give the viewer a big-picture understanding of this topic. "
            f"Use an everyday analogy that ties everything together. 4-5 sentences."
        )

    elif scene_type == "QuoteScene":
        quote = scene.get("quote", "")
        instruction = (
            f"The screen shows this key takeaway: '{quote}'. "
            f"Explain what this means in simple words. "
            f"Tell the viewer why this is the single most important thing to remember. "
            f"Give a practical example of how this applies in real life or exams. 4-5 sentences."
        )

    elif scene_type == "OutroScene":
        summary = scene.get("summary", "")
        instruction = (
            f"The video is ending. The summary on screen says: {summary}. "
            f"Recap the 3 most important things learned in this video. "
            f"Motivate the viewer to keep studying. "
            f"End warmly and encourage them to watch the next video. 5-6 sentences."
        )

    else:
        return ""

    print(f"Calling Groq for scene {scene.get('type')}")

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: groq_client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert educational video narrator who sounds like an enthusiastic, "
                                "friendly teacher. You explain things clearly with real-life examples and analogies. "
                                "You never just read what's on screen — you always add more context and explanation. "
                                "Keep your narration natural, conversational, and engaging. "
                                "Do NOT use bullet points, headers, or formatting. "
                                f"Write your ENTIRE response in {target_language} only, as if you are talking "
                                f"to a student who speaks {target_language} natively. "
                                f"Do not mix in English unless a term has no natural {target_language} equivalent."
                            ),
                        },
                        {
                            "role": "user",
                            "content": instruction,
                       },
                   ],
                   temperature=0.7,
                   max_tokens=300,
                )
           ),
           timeout=60,
        )

        print(f"Groq finished for scene {scene.get('type')}")

    except asyncio.TimeoutError:
        raise Exception("Groq request timed out after 60 seconds")

    return response.choices[0].message.content.strip()

async def generate_audio_for_scene(
    scene: dict,
    scene_index: int,
    video_id: str,
    voice: str,
    language: str,
) -> dict:
    ensure_audio_dir()
    print(f"Generating narration for scene {scene_index}")
    narration =  await scene_to_narration(scene, language)
    print(f"Narration generated for scene {scene_index}")
    if not narration.strip():
        return {
            "scene_index": scene_index,
            "audio_file": None,
            "audio_filename": None,
            "narration": "",
            "duration_seconds": 3.0,
            "duration_frames": 90,
        }

    audio_filename = f"{video_id}_scene_{scene_index:02d}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)

    communicate = edge_tts.Communicate(narration, voice)
    print(f"Generating TTS for scene {scene_index}")
    try:
        await asyncio.wait_for(
            communicate.save(audio_path),
            timeout=60
        )
    except asyncio.TimeoutError:
        raise Exception("Edge TTS timed out")
    print(f"TTS finished for scene {scene_index}")

    duration = await get_audio_duration(audio_path)

    return {
        "scene_index": scene_index,
        "audio_file": audio_path,
        "audio_filename": audio_filename,
        "narration": narration,
        "duration_seconds": duration,
        "duration_frames": int(duration * 30) + 30,
    }


async def get_audio_duration(audio_path: str) -> float:
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        return audio.info.length
    except ImportError:
        file_size = os.path.getsize(audio_path)
        estimated_duration = file_size / 3000
        return max(estimated_duration, 2.0)


async def generate_all_audio(
    scenes: list,
    video_id: str,
    plan: str = "premium",
    language: str = "english",
    voice: str = None,
) -> list:
    """
    - Free plan: no audio at all — silent placeholders sized to each
      scene's default on-screen duration.
    - Basic/Premium: uses the explicitly requested voice if given and
      valid for this plan/language, otherwise auto-picks one.
    """
    if not PLAN_HAS_AUDIO.get(plan, True):
        results = []
        for index, scene in enumerate(scenes):
            scene_type = scene.get("type", "TitleIntro")
            frames = SCENE_DURATIONS_NO_AUDIO.get(scene_type, 150)
            results.append({
                "scene_index": index,
                "audio_file": None,
                "audio_filename": None,
                "narration": "",
                "duration_seconds": round(frames / 30, 1),
                "duration_frames": frames,
            })
        return results

    resolved_voice = voice or pick_voice(plan, language)

    results = []

    for index, scene in enumerate(scenes):
        print(f"Generating audio for scene {index + 1}/{len(scenes)}")

        result = await generate_audio_for_scene(
            scene,
            index,
            video_id,
            resolved_voice,
            language,
        )

        results.append(result)

    return results


def generate_audio_sync(scenes: list, video_id: str, plan: str = "premium", language: str = "english", voice: str = None) -> list:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(generate_all_audio(scenes, video_id, plan, language, voice))
        else:
            return asyncio.run(generate_all_audio(scenes, video_id, plan, language, voice))
    except RuntimeError:
        return asyncio.run(generate_all_audio(scenes, video_id, plan, language, voice))