import os
import json
from groq import Groq
from dotenv import load_dotenv
from validator import validate_and_clean_scenes

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_scene_json(extracted_text: str, target_scene_count: int = None) -> list:
    """
    Sends extracted text to Groq (LLaMA) and gets back
    a structured list of scenes to render in Remotion.

    target_scene_count: approximate number of scenes to generate, used to
    hit a requested video duration. If None, falls back to Groq's own
    judgement (5-8 scenes), same as before duration selection existed.
    """

    if target_scene_count:
        scene_count_instruction = (
            f"- Generate exactly {target_scene_count} scenes total. This number is "
            f"calculated from the requested video length, so it matters — do not "
            f"generate more or fewer than this. If the source content is thin, go "
            f"deeper into related sub-points, examples, and context rather than "
            f"repeating the same point — never pad with filler, and never skip content "
            f"just to hit the number."
        )
    else:
        scene_count_instruction = "- Generate between 5 and 8 scenes total (not too short, not too long)"

    system_prompt = f"""
You are an expert educational video script writer for a platform called Vidora.

Your job is to read any educational text (from a PDF, notes, or research paper) 
and convert it into a structured list of video scenes.

You must return ONLY a valid JSON array — no explanation, no markdown, no backticks.
Just the raw JSON array starting with [ and ending with ].

Each scene in the array must follow EXACTLY one of these formats:

1. Title scene (always first):
{{"type": "TitleIntro", "topic": "The main topic in a short phrase"}}

2. Definition scene:
{{"type": "DefinitionScene", "term": "The key term", "explanation": "Clear explanation in simple words"}}

3. Bullet points scene:
{{"type": "BulletScene", "heading": "Section heading", "points": ["point 1", "point 2", "point 3"]}}

4. Comparison scene:
{{"type": "ComparisonScene", "heading": "X vs Y", "leftTitle": "X", "leftPoints": ["point1", "point2"], "rightTitle": "Y", "rightPoints": ["point1", "point2"]}}

5. Diagram/process scene:
{{"type": "DiagramScene", "heading": "Process name", "steps": ["Step 1", "Step 2", "Step 3", "Step 4"]}}

6. Timeline scene:
{{"type": "TimelineScene", "heading": "Timeline heading", "events": [{{"year": "1900", "label": "Event description"}}, {{"year": "1950", "label": "Event description"}}]}}

7. Statistics scene:
{{"type": "StatsScene", "label": "Did You Know?", "number": 86, "suffix": "Billion", "description": "Explanation of the statistic"}}

8. Icon grid scene:
{{"type": "IconGridScene", "heading": "Section heading", "description": "Brief description", "iconNames": ["Brain", "Zap", "Heart", "Atom", "Microscope", "BookOpen"]}}

9. Key takeaway scene:
{{"type": "QuoteScene", "quote": "The most important takeaway from this section", "attribution": "Key Takeaway"}}

10. Outro scene (always last):
{{"type": "OutroScene", "summary": "2-3 sentence summary of the entire topic", "ctaText": "Watch Next Video"}}

Rules:
- Always start with TitleIntro and end with OutroScene
{scene_count_instruction}
- Choose scene types that best fit the content
- For higher scene counts, it's fine to reuse a scene type multiple times
  (e.g. several BulletScene or DefinitionScene entries) as long as each
  covers a genuinely different sub-topic — never repeat the same content twice
- Keep all text concise and simple — this is for educational videos
- For IconGridScene, only use these valid icon names: Brain, Zap, Heart, Atom, Microscope, BookOpen, Wallet, Award, Coins, TrendingUp, Droplet, Percent, Sun, Moon, Leaf, Calculator, BarChart3, Globe, Shield, Star
- Return ONLY the JSON array, nothing else
"""

    user_prompt = f"""
Here is the educational content to convert into video scenes:

{extracted_text[:4000]}

Convert this into a JSON array of video scenes following the format above.
"""

    max_tokens = 2000
    if target_scene_count:
        max_tokens = min(max(2000, target_scene_count * 230), 8000)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=max_tokens,
    )

    raw_response = response.choices[0].message.content.strip()

    if raw_response.startswith("```"):
        raw_response = raw_response.split("```")[1]
        if raw_response.startswith("json"):
            raw_response = raw_response[4:]
    raw_response = raw_response.strip()

    raw_scenes = json.loads(raw_response)
    result = validate_and_clean_scenes(raw_scenes)
    return result