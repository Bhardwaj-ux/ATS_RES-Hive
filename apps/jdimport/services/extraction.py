import json
import os
import re

import requests

EXTRACTION_PROMPT = """You are extracting structured job posting data from a job description document written in Markdown syntax.

Read the markdown content below and return ONLY a single valid JSON object (no markdown fences, no commentary) with exactly these keys:

- "title": string, the job title
- "department": string, department or team name, empty string if not found
- "location": string, work location city, empty string if not found
- "employment_type": one of "full_time", "part_time", "intern", "contract" (best guess, default "full_time")
- "experience_min_years": integer, minimum years of experience required, 0 if not specified
- "experience_max_years": integer, maximum years of experience required, same as min if not specified or unclear
- "skills": array of strings, individual required/preferred skills, deduplicated, each a short skill/tool name (not long phrases), add 10 to 15 more relevant skills that you feel are important for the job-title (all in comma-separtated strings in the array)
- "description": string, a clean rewritten role summary/responsibilities section in plain text paragraphs (no markdown symbols), 5-7 sentences
- "requirements": string, a clean rewritten requirements/qualifications section in plain text, using short paragraphs and/or simple "- " bullet lines & well-formatting

Do not invent information that is not present in the source text. If a field cannot be determined, use an empty string, 0, or an empty array as appropriate for its type.

Markdown content:
---
{content}
---
"""

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


class ExtractionError(Exception):
    pass


def extract_job_fields(markdown_text: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ExtractionError("GEMINI_API_KEY is not configured.")

    prompt = EXTRACTION_PROMPT.format(content=markdown_text[:20000])

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data_json = response.json()
    except requests.exceptions.RequestException as exc:
        raise ExtractionError(f"Gemini request failed: {exc}") from exc
    except ValueError as exc:
        raise ExtractionError(f"Gemini returned a non-JSON response: {exc}") from exc

    try:
        candidates = data_json.get("candidates") or []
        if not candidates:
            raise KeyError("candidates")
        parts = candidates[0]["content"]["parts"]
        raw_text = "".join(part.get("text", "") for part in parts).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ExtractionError(
            f"Unexpected Gemini response shape: {exc} | raw={data_json}"
        ) from exc

    raw_text = re.sub(r"^```(json)?", "", raw_text).strip()
    raw_text = re.sub(r"```$", "", raw_text).strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(
            f"Could not parse the AI response as JSON: {exc}"
        ) from exc

    return _normalize(data)


def _normalize(data: dict) -> dict:
    def to_int(value, default=0):
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return default

    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    clean_skills = []
    seen = set()
    for skill in skills:
        skill = str(skill).strip()
        if not skill:
            continue
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        clean_skills.append(skill)

    employment_type = str(data.get("employment_type") or "full_time").strip().lower()
    if employment_type not in {"full_time", "part_time", "intern", "contract"}:
        employment_type = "full_time"

    exp_min = to_int(data.get("experience_min_years"), 0)
    exp_max = to_int(data.get("experience_max_years"), exp_min)
    if exp_max < exp_min:
        exp_max = exp_min

    return {
        "title": str(data.get("title") or "").strip(),
        "department": str(data.get("department") or "").strip(),
        "location": str(data.get("location") or "").strip(),
        "employment_type": employment_type,
        "experience_min_years": exp_min,
        "experience_max_years": exp_max,
        "skills": clean_skills,
        "description": str(data.get("description") or "").strip(),
        "requirements": str(data.get("requirements") or "").strip(),
    }
