"""
validator.py
Cleans and validates the scene JSON returned by Groq.
Makes sure every scene maps to a known Remotion template
and has all required fields with correct types.
"""

# All valid scene types — must match your Remotion component names exactly
VALID_SCENE_TYPES = {
    "TitleIntro",
    "DefinitionScene",
    "BulletScene",
    "ComparisonScene",
    "DiagramScene",
    "TimelineScene",
    "StatsScene",
    "IconGridScene",
    "QuoteScene",
    "OutroScene",
}

# Valid Lucide icon names your IconGridScene supports
VALID_ICON_NAMES = {
    "Brain", "Zap", "Heart", "Atom", "Microscope", "BookOpen",
    "Wallet", "Award", "Coins", "TrendingUp", "Droplet", "Percent",
    "Sun", "Moon", "Leaf", "Calculator", "BarChart3", "Globe",
    "Shield", "Star", "Circle",
}


def validate_title_intro(scene: dict) -> dict:
    return {
        "type": "TitleIntro",
        "topic": str(scene.get("topic", "Untitled Topic"))[:80],
    }


def validate_definition_scene(scene: dict) -> dict:
    return {
        "type": "DefinitionScene",
        "term": str(scene.get("term", "Key Term"))[:40],
        "explanation": str(scene.get("explanation", "No explanation provided."))[:200],
    }


def validate_bullet_scene(scene: dict) -> dict:
    raw_points = scene.get("points", [])
    # Make sure points is a list of strings, max 4 points
    if not isinstance(raw_points, list):
        raw_points = [str(raw_points)]
    clean_points = [str(p)[:120] for p in raw_points[:4]]
    if not clean_points:
        clean_points = ["No points provided"]
    return {
        "type": "BulletScene",
        "heading": str(scene.get("heading", "Key Points"))[:60],
        "points": clean_points,
    }


def validate_comparison_scene(scene: dict) -> dict:
    left_points = scene.get("leftPoints", [])
    right_points = scene.get("rightPoints", [])
    if not isinstance(left_points, list):
        left_points = [str(left_points)]
    if not isinstance(right_points, list):
        right_points = [str(right_points)]
    return {
        "type": "ComparisonScene",
        "heading": str(scene.get("heading", "Comparison"))[:60],
        "leftTitle": str(scene.get("leftTitle", "Option A"))[:30],
        "leftPoints": [str(p)[:100] for p in left_points[:3]],
        "rightTitle": str(scene.get("rightTitle", "Option B"))[:30],
        "rightPoints": [str(p)[:100] for p in right_points[:3]],
    }


def validate_diagram_scene(scene: dict) -> dict:
    raw_steps = scene.get("steps", [])
    if not isinstance(raw_steps, list):
        raw_steps = [str(raw_steps)]
    clean_steps = [str(s)[:80] for s in raw_steps[:4]]
    if not clean_steps:
        clean_steps = ["Step 1", "Step 2", "Step 3"]
    return {
        "type": "DiagramScene",
        "heading": str(scene.get("heading", "Process"))[:60],
        "steps": clean_steps,
    }


def validate_timeline_scene(scene: dict) -> dict:
    raw_events = scene.get("events", [])
    if not isinstance(raw_events, list):
        raw_events = []
    clean_events = []
    for e in raw_events[:5]:
        if isinstance(e, dict):
            clean_events.append({
                "year": str(e.get("year", "?"))[:10],
                "label": str(e.get("label", "Event"))[:80],
            })
    if not clean_events:
        clean_events = [{"year": "2024", "label": "Event"}]
    return {
        "type": "TimelineScene",
        "heading": str(scene.get("heading", "Timeline"))[:60],
        "events": clean_events,
    }


def validate_stats_scene(scene: dict) -> dict:
    # Make sure number is actually a number
    try:
        number = float(scene.get("number", 0))
        number = int(number) if number == int(number) else number
    except (ValueError, TypeError):
        number = 0
    return {
        "type": "StatsScene",
        "label": str(scene.get("label", "Did You Know?"))[:40],
        "number": number,
        "suffix": str(scene.get("suffix", ""))[:20],
        "description": str(scene.get("description", ""))[:200],
    }


def validate_icon_grid_scene(scene: dict) -> dict:
    raw_icons = scene.get("iconNames", [])
    if not isinstance(raw_icons, list):
        raw_icons = []
    # Filter out any icon names that don't exist in Lucide
    clean_icons = [
        icon for icon in raw_icons if icon in VALID_ICON_NAMES
    ]
    # If none are valid, use safe defaults
    if not clean_icons:
        clean_icons = ["BookOpen", "Brain", "Star", "Globe", "Atom", "Zap"]
    return {
        "type": "IconGridScene",
        "heading": str(scene.get("heading", "Key Concepts"))[:60],
        "description": str(scene.get("description", ""))[:200],
        "iconNames": clean_icons[:6],
    }


def validate_quote_scene(scene: dict) -> dict:
    return {
        "type": "QuoteScene",
        "quote": str(scene.get("quote", "Knowledge is power."))[:200],
        "attribution": str(scene.get("attribution", "Key Takeaway"))[:40],
    }


def validate_outro_scene(scene: dict) -> dict:
    return {
        "type": "OutroScene",
        "summary": str(scene.get("summary", "Thanks for watching!"))[:300],
        "ctaText": str(scene.get("ctaText", "Watch Next Video"))[:40],
    }


# Map each scene type to its validator function
VALIDATORS = {
    "TitleIntro": validate_title_intro,
    "DefinitionScene": validate_definition_scene,
    "BulletScene": validate_bullet_scene,
    "ComparisonScene": validate_comparison_scene,
    "DiagramScene": validate_diagram_scene,
    "TimelineScene": validate_timeline_scene,
    "StatsScene": validate_stats_scene,
    "IconGridScene": validate_icon_grid_scene,
    "QuoteScene": validate_quote_scene,
    "OutroScene": validate_outro_scene,
}


def validate_and_clean_scenes(raw_scenes: list) -> dict:
    """
    Main function — takes raw Groq output and returns
    a clean, validated, safe list of scenes.

    Returns:
        {
            "valid": True/False,
            "scenes": [...cleaned scenes...],
            "warnings": [...any issues found and fixed...]
        }
    """
    warnings = []
    cleaned = []

    if not isinstance(raw_scenes, list):
        return {
            "valid": False,
            "scenes": [],
            "warnings": ["Groq did not return a list — cannot process."]
        }

    if len(raw_scenes) == 0:
        return {
            "valid": False,
            "scenes": [],
            "warnings": ["Groq returned an empty list."]
        }

    for index, scene in enumerate(raw_scenes):
        # Must be a dict
        if not isinstance(scene, dict):
            warnings.append(f"Scene {index + 1} is not an object — skipped.")
            continue

        scene_type = scene.get("type", "")

        # Must have a known type
        if scene_type not in VALID_SCENE_TYPES:
            warnings.append(
                f"Scene {index + 1} has unknown type '{scene_type}' — skipped."
            )
            continue

        # Run through the validator for this scene type
        try:
            clean_scene = VALIDATORS[scene_type](scene)
            cleaned.append(clean_scene)
        except Exception as e:
            warnings.append(
                f"Scene {index + 1} ({scene_type}) failed validation: {str(e)} — skipped."
            )

    # Make sure video always starts with TitleIntro
    if cleaned and cleaned[0]["type"] != "TitleIntro":
        warnings.append("First scene was not TitleIntro — added one automatically.")
        cleaned.insert(0, {
            "type": "TitleIntro",
            "topic": "Educational Video"
        })

    # Make sure video always ends with OutroScene
    if cleaned and cleaned[-1]["type"] != "OutroScene":
        warnings.append("Last scene was not OutroScene — added one automatically.")
        cleaned.append({
            "type": "OutroScene",
            "summary": "Thank you for watching this educational video.",
            "ctaText": "Watch Next Video"
        })

    return {
        "valid": len(cleaned) > 0,
        "scenes": cleaned,
        "warnings": warnings,
    }