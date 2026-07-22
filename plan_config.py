"""
plan_config.py
Central definitions for what each subscription plan unlocks:
video quota, audio narration availability, language/voice options,
and available video durations.
"""

import random

PLAN_LIMITS = {
    "free": 1,
    "basic": 5,
    "premium": 22,
}

LANGUAGE_VOICES = {
    "english": ["en-US-AriaNeural", "en-US-GuyNeural", "en-IN-NeerjaNeural"],
    "hindi": ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"],
    "spanish": ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"],
    "french": ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"],
    "german": ["de-DE-KatjaNeural", "de-DE-ConradNeural"],
    "tamil": ["ta-IN-PallaviNeural", "ta-IN-ValluvarNeural"],
    "telugu": ["te-IN-ShrutiNeural", "te-IN-MohanNeural"],
    "japanese": ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"],
}

PLAN_LANGUAGES = {
    "free": [],
    "basic": ["english", "hindi"],
    "premium": list(LANGUAGE_VOICES.keys()),
}

PLAN_HAS_AUDIO = {
    "free": False,
    "basic": True,
    "premium": True,
}

PLAN_DURATIONS = {
    "free": [3],
    "basic": [1, 3, 5, 7],
    "premium": [1, 2, 5, 7, 10, 15, 20],
}

SCENE_DURATIONS_NO_AUDIO = {
    "TitleIntro": 150,
    "DefinitionScene": 180,
    "BulletScene": 210,
    "ComparisonScene": 270,
    "DiagramScene": 270,
    "TimelineScene": 270,
    "StatsScene": 210,
    "IconGridScene": 240,
    "QuoteScene": 180,
    "OutroScene": 210,
}


def get_voices_for_language(plan: str, language: str) -> list:
    voices = LANGUAGE_VOICES.get(language, [])
    if plan == "basic":
        basic_voices = LANGUAGE_VOICES["english"][:3] + LANGUAGE_VOICES["hindi"][:2]
        voices = [v for v in voices if v in basic_voices] or voices
    return voices


def get_plan_voices_by_language(plan: str) -> dict:
    languages = PLAN_LANGUAGES.get(plan, [])
    return {lang: get_voices_for_language(plan, lang) for lang in languages}


def pick_voice(plan: str, language: str) -> str:
    voices = get_voices_for_language(plan, language) or LANGUAGE_VOICES.get(language, LANGUAGE_VOICES["english"])
    return random.choice(voices)


def estimate_scene_count(minutes: float, has_audio: bool) -> int:
    """
    Rough estimate of how many scenes are needed to hit a requested video
    length. This is a target, not a guarantee — actual length depends on
    how long Groq's narration ends up being for each scene.

    Floor is 3 (TitleIntro + 1 content scene + OutroScene) — the minimum
    structurally possible — not 5. A higher floor was previously forcing
    short 1-2 minute requests to generate 5+ scenes regardless of the
    actual math, badly overshooting the requested duration.
    """
    target_seconds = minutes * 60
    avg_scene_seconds = 40 if has_audio else 7.5
    count = round(target_seconds / avg_scene_seconds)
    return max(3, min(count, 40))