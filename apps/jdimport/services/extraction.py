# FILEPATH: apps/jdimport/services/extraction.py
import re
import markdown as md_lib
from flashtext import KeywordProcessor

DEPARTMENT_KEYWORDS = {
    "Sales": ["sales", "business development", "bd executive"],
    "ODM": ["odm", "original design manufacturer"],
    "Box Build": ["box build", "assembly", "smt", "pcba"],
    "Human Resources": [
        "human resources",
        "hr ",
        "hr executive",
        "talent acquisition",
        "recruiter",
    ],
    "XOR": ["xor"],
    "Marketing": ["marketing", "branding", "digital marketing", "content strategy"],
    "Finance": ["finance", "accounts", "accounting", "audit", "taxation"],
    "IT & Admin": [
        "it support",
        "system admin",
        "network admin",
        "it & admin",
        "infrastructure",
    ],
}

CITY_KEYWORDS = {
    "Bengaluru": ["bengaluru", "bangalore", "blr"],
    "Delhi": ["delhi", "new delhi"],
    "Gurugram": ["gurugram", "gurgaon"],
}

EMPLOYMENT_TYPE_KEYWORDS = {
    "full_time": ["full time", "full-time", "permanent"],
    "part_time": ["part time", "part-time"],
    "intern": ["intern", "internship"],
    "contract": ["contract", "contractual", "temporary"],
}

SKILL_LIBRARY = [
    "python",
    "django",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "sql",
    "postgresql",
    "mysql",
    "excel",
    "power bi",
    "tableau",
    "sap",
    "salesforce",
    "communication",
    "leadership",
    "project management",
    "negotiation",
    "customer relationship management",
    "crm",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "html",
    "css",
    "figma",
    "adobe photoshop",
    "seo",
    "sem",
    "content writing",
    "recruitment",
    "onboarding",
    "payroll",
    "compliance",
    "accounting",
    "taxation",
    "gst",
    "audit",
    "budgeting",
    "supply chain",
    "logistics",
    "quality control",
    "six sigma",
    "lean manufacturing",
    "pcb design",
    "soldering",
    "smt",
    "autocad",
    "solidworks",
    "embedded systems",
]

SECTION_HEADING_PATTERNS = [
    r"roles?\s*(and|&)?\s*responsibilities",
    r"key\s*responsibilities",
    r"job\s*responsibilities",
    r"responsibilities",
    r"duties",
]

REQUIREMENTS_HEADING_PATTERNS = [
    r"requirements?",
    r"qualifications?",
    r"skills?\s*(and|&)?\s*qualifications",
    r"who\s*you\s*are",
    r"what\s*we.?re\s*looking\s*for",
]


class ExtractionError(Exception):
    pass


def _find_experience_years(text):
    match = re.search(
        r"(\d+)\s*(?:\+|to|-|–)?\s*(\d+)?\s*years?\s*(?:of)?\s*experience",
        text,
        re.IGNORECASE,
    )
    if not match:
        return 0, 0
    low = int(match.group(1))
    high = int(match.group(2)) if match.group(2) else low
    return low, max(low, high)


def _find_title(markdown_text):
    for line in markdown_text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped and len(stripped) < 100:
            return stripped
    return "Untitled Role"


def _match_keyword_map(text, keyword_map, default=""):
    lowered = text.lower()
    for label, keywords in keyword_map.items():
        for kw in keywords:
            if kw in lowered:
                return label
    return default


def _split_section(markdown_text, heading_patterns, stop_patterns):
    """
    Finds a heading matching heading_patterns and returns the markdown content
    below it, stopping at the next heading in stop_patterns (or end of text).
    """
    lines = markdown_text.splitlines()
    heading_regex = re.compile(
        r"^#{1,6}\s*(" + "|".join(heading_patterns) + r")\s*:?\s*$", re.IGNORECASE
    )
    stop_regex = re.compile(
        r"^#{1,6}\s*(" + "|".join(stop_patterns) + r")\s*:?\s*$", re.IGNORECASE
    )
    plain_heading_regex = re.compile(
        r"^\**\s*(" + "|".join(heading_patterns) + r")\s*\**\s*:?\s*$", re.IGNORECASE
    )

    start_index = None
    for i, line in enumerate(lines):
        if heading_regex.match(line.strip()) or plain_heading_regex.match(line.strip()):
            start_index = i + 1
            break

    if start_index is None:
        return ""

    collected = []
    for line in lines[start_index:]:
        if stop_regex.match(line.strip()) or re.match(r"^#{1,6}\s+", line.strip()):
            if collected:
                break
            continue
        collected.append(line)

    return "\n".join(collected).strip()


def _markdown_to_clean_html(markdown_text):
    """Renders markdown to HTML for storage in the rich-text-editor field."""
    if not markdown_text.strip():
        return ""
    html = md_lib.markdown(markdown_text, extensions=["extra", "sane_lists", "nl2br"])
    return html.strip()


def _extract_skills(text):
    processor = KeywordProcessor(case_sensitive=False)
    for skill in SKILL_LIBRARY:
        processor.add_keyword(skill)
    found = processor.extract_keywords(text)
    seen = set()
    cleaned = []
    for item in found:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item.title() if item.islower() else item)
    return cleaned


def extract_job_fields(markdown_text):
    if not markdown_text or not markdown_text.strip():
        raise ExtractionError("No content available to extract job details from.")

    title = _find_title(markdown_text)
    department = _match_keyword_map(markdown_text, DEPARTMENT_KEYWORDS, default="")
    location = _match_keyword_map(markdown_text, CITY_KEYWORDS, default="")
    employment_type = _match_keyword_map(
        markdown_text, EMPLOYMENT_TYPE_KEYWORDS, default="full_time"
    )
    exp_min, exp_max = _find_experience_years(markdown_text)

    responsibilities_md = _split_section(
        markdown_text, SECTION_HEADING_PATTERNS, REQUIREMENTS_HEADING_PATTERNS
    )
    requirements_md = _split_section(
        markdown_text, REQUIREMENTS_HEADING_PATTERNS, SECTION_HEADING_PATTERNS
    )

    if not responsibilities_md:
        # Fallback: use the whole document body (minus the title line) as responsibilities.
        body_lines = markdown_text.splitlines()[1:]
        responsibilities_md = "\n".join(body_lines).strip()

    responsibilities_html = _markdown_to_clean_html(responsibilities_md)
    description_text = requirements_md if requirements_md else responsibilities_md[:600]

    skills = _extract_skills(markdown_text)

    return {
        "title": title,
        "department": department,
        "location": location,
        "employment_type": employment_type,
        "experience_min_years": exp_min,
        "experience_max_years": exp_max,
        "description": description_text[:2000],
        "requirements": responsibilities_html,
        "skills": skills,
    }
