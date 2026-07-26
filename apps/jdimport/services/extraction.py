# import json
# import os
# import re
# import time
# import requests

# EXTRACTION_PROMPT = """You are extracting structured job posting data from a job description document written in Markdown syntax.

# Read the markdown content below and return ONLY a single valid JSON object (no markdown fences, no commentary) with exactly these keys:

# - "title": string, the job title
# - "department": string, department or team name, empty string if not found
# - "location": string, work location city, empty string if not found
# - "employment_type": one of "full_time", "part_time", "intern", "contract" (best guess, default "full_time")
# - "experience_min_years": integer, minimum years of experience required, 0 if not specified
# - "experience_max_years": integer, maximum years of experience required, same as min if not specified or unclear
# - "skills": array of strings, individual required/preferred skills, deduplicated, each a short skill/tool name (not long phrases), add 10 to 15 more relevant skills that you feel are important for the job-title (all in comma-separtated strings in the array)
# - "description": string, a clean rewritten role summary/responsibilities section in plain text paragraphs (no markdown symbols), 5-7 sentences
# - "requirements": string, a clean rewritten requirements/qualifications section in plain text, using short paragraphs and/or simple "- " bullet lines & well-formatting

# Do not invent information that is not present in the source text. If a field cannot be determined, use an empty string, 0, or an empty array as appropriate for its type.

# Markdown content:
# ---
# {content}
# ---
# """

# GEMINI_MODEL = "gemini-2.0-flash"
# GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# MAX_RETRIES = 4
# BASE_BACKOFF_SECONDS = 3


# class ExtractionError(Exception):
#     pass


# def _call_gemini_with_retry(payload, api_key):
#     """
#     Retries on HTTP 429 (rate limit) with exponential backoff, respecting
#     the server's Retry-After header when it provides one. Other errors
#     (4xx auth issues, 5xx server errors) are not retried and raise
#     immediately, since retrying those would just waste time.
#     """
#     last_error = None

#     for attempt in range(MAX_RETRIES):
#         try:
#             response = requests.post(
#                 GEMINI_URL,
#                 params={"key": api_key},
#                 json=payload,
#                 timeout=60,
#             )
#         except requests.exceptions.RequestException as exc:
#             raise ExtractionError(f"Gemini request failed: {exc}") from exc

#         if response.status_code == 429:
#             retry_after = response.headers.get("Retry-After")
#             if retry_after:
#                 try:
#                     wait_seconds = float(retry_after)
#                 except ValueError:
#                     wait_seconds = BASE_BACKOFF_SECONDS * (2**attempt)
#             else:
#                 wait_seconds = BASE_BACKOFF_SECONDS * (2**attempt)

#             last_error = f"Rate limited (429) after {attempt + 1} attempt(s)."
#             if attempt < MAX_RETRIES - 1:
#                 time.sleep(wait_seconds)
#                 continue
#             raise ExtractionError(
#                 f"Gemini is rate-limiting requests. Please wait a minute and try "
#                 f"importing fewer files at once, or upgrade your Gemini API quota. "
#                 f"({last_error})"
#             )

#         try:
#             response.raise_for_status()
#         except requests.exceptions.HTTPError as exc:
#             raise ExtractionError(f"Gemini request failed: {exc}") from exc

#         try:
#             return response.json()
#         except ValueError as exc:
#             raise ExtractionError(
#                 f"Gemini returned a non-JSON response: {exc}"
#             ) from exc

#     raise ExtractionError(last_error or "Gemini request failed after retries.")


# def extract_job_fields(markdown_text: str) -> dict:
#     api_key = os.getenv("GEMINI_API_KEY", "").strip()
#     if not api_key:
#         raise ExtractionError("GEMINI_API_KEY is not configured.")

#     prompt = EXTRACTION_PROMPT.format(content=markdown_text[:20000])

#     payload = {
#         "contents": [{"parts": [{"text": prompt}]}],
#         "generationConfig": {
#             "temperature": 0.2,
#             "responseMimeType": "application/json",
#         },
#     }

#     data_json = _call_gemini_with_retry(payload, api_key)

#     try:
#         candidates = data_json.get("candidates") or []
#         if not candidates:
#             raise KeyError("candidates")
#         parts = candidates[0]["content"]["parts"]
#         raw_text = "".join(part.get("text", "") for part in parts).strip()
#     except (KeyError, IndexError, TypeError) as exc:
#         raise ExtractionError(
#             f"Unexpected Gemini response shape: {exc} | raw={data_json}"
#         ) from exc

#     raw_text = re.sub(r"^```(json)?", "", raw_text).strip()
#     raw_text = re.sub(r"```$", "", raw_text).strip()

#     try:
#         data = json.loads(raw_text)
#     except json.JSONDecodeError as exc:
#         raise ExtractionError(
#             f"Could not parse the AI response as JSON: {exc}"
#         ) from exc

#     return _normalize(data)


# def _normalize(data: dict) -> dict:
#     def to_int(value, default=0):
#         try:
#             return max(0, int(value))
#         except (TypeError, ValueError):
#             return default

#     skills = data.get("skills") or []
#     if isinstance(skills, str):
#         skills = [s.strip() for s in skills.split(",") if s.strip()]
#     clean_skills = []
#     seen = set()
#     for skill in skills:
#         skill = str(skill).strip()
#         if not skill:
#             continue
#         key = skill.lower()
#         if key in seen:
#             continue
#         seen.add(key)
#         clean_skills.append(skill)

#     employment_type = str(data.get("employment_type") or "full_time").strip().lower()
#     if employment_type not in {"full_time", "part_time", "intern", "contract"}:
#         employment_type = "full_time"

#     exp_min = to_int(data.get("experience_min_years"), 0)
#     exp_max = to_int(data.get("experience_max_years"), exp_min)
#     if exp_max < exp_min:
#         exp_max = exp_min

#     return {
#         "title": str(data.get("title") or "").strip(),
#         "department": str(data.get("department") or "").strip(),
#         "location": str(data.get("location") or "").strip(),
#         "employment_type": employment_type,
#         "experience_min_years": exp_min,
#         "experience_max_years": exp_max,
#         "skills": clean_skills,
#         "description": str(data.get("description") or "").strip(),
#         "requirements": str(data.get("requirements") or "").strip(),
#     }


import re
from flashtext import KeywordProcessor

# GEMINI_API_KEY is no longer used by this module. It's safe to leave the
# env var in place (unused) or remove it — this extractor makes zero
# network calls.


class ExtractionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Skill vocabulary. flashtext matches these as whole-word phrases, case
# insensitive, in a single pass over the document regardless of vocabulary
# size (unlike a loop of regexes, which gets slow and error-prone past a
# few dozen terms).
# ---------------------------------------------------------------------------
SKILLS_VOCAB = [
    # Software / general engineering
    "Python",
    "Java",
    "C",
    "C++",
    "C#",
    "JavaScript",
    "TypeScript",
    "Go",
    "Rust",
    "SQL",
    "NoSQL",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Django",
    "Flask",
    "FastAPI",
    "React",
    "Angular",
    "Vue",
    "Node.js",
    "REST API",
    "GraphQL",
    "Docker",
    "Kubernetes",
    "AWS",
    "Azure",
    "GCP",
    "CI/CD",
    "Git",
    "Linux",
    "Microservices",
    "Machine Learning",
    "Deep Learning",
    "Data Science",
    "TensorFlow",
    "PyTorch",
    "NLP",
    "Computer Vision",
    "Pandas",
    "NumPy",
    "Power BI",
    "Tableau",
    "Excel",
    "ETL",
    "Data Analysis",
    "Data Visualization",
    "Agile",
    "Scrum",
    "Jira",
    "System Design",
    "API Design",
    "Unit Testing",
    # Embedded / hardware / firmware
    "Embedded C",
    "Embedded Systems",
    "Firmware Development",
    "RTOS",
    "Yocto",
    "Buildroot",
    "U-Boot",
    "Device Drivers",
    "Linux Kernel",
    "Board Bring-up",
    "SoC",
    "ARM Architecture",
    "ARMv7",
    "ARMv8",
    "VLSI",
    "PCB Design",
    "FPGA",
    "Verilog",
    "VHDL",
    "I2C",
    "SPI",
    "UART",
    "CAN Bus",
    "IoT",
    "Microcontrollers",
    "Schematic Design",
    "Signal Processing",
    "Power Electronics",
    # HR / Talent
    "Talent Acquisition",
    "Recruitment",
    "Onboarding",
    "HRBP",
    "Employee Relations",
    "Performance Management",
    "Compensation & Benefits",
    "HR Policies",
    "Stakeholder Management",
    "Workforce Planning",
    "HRIS",
    "Payroll",
    # Sales / Business
    "Sales Strategy",
    "Business Development",
    "Account Management",
    "Lead Generation",
    "CRM",
    "Salesforce",
    "Negotiation",
    "Client Relationship Management",
    "Market Research",
    "B2B Sales",
    "B2C Sales",
    "Cold Calling",
    # Supply chain / operations
    "Supply Chain Management",
    "Procurement",
    "Vendor Management",
    "Logistics",
    "Inventory Management",
    "SAP",
    "ERP",
    "Demand Planning",
    "Warehouse Management",
    "Quality Control",
    "Six Sigma",
    "Lean Manufacturing",
    # Project / program management
    "Project Management",
    "Program Management",
    "Risk Management",
    "Budgeting",
    "Stakeholder Communication",
    "Roadmap Planning",
    "PMP",
    "Kanban",
    # IT / technical support
    "Technical Support",
    "Help Desk",
    "Troubleshooting",
    "IT Infrastructure",
    "Networking",
    "Active Directory",
    "ITIL",
    "Ticketing Systems",
    # Finance
    "Financial Analysis",
    "Accounting",
    "Budgeting",
    "Forecasting",
    "Auditing",
    "Taxation",
    "Financial Modeling",
    "GAAP",
    "Bookkeeping",
]

# ---------------------------------------------------------------------------
# Role-category detection -> a bounded set of commonly-paired skills. This is
# an explicit, static heuristic (NOT AI inference) that approximates the old
# "suggest extra relevant skills" behaviour without pretending to generate
# knowledge that isn't there. Keep specific categories before generic ones.
# ---------------------------------------------------------------------------
ROLE_CATEGORY_KEYWORDS = [
    ("embedded", ["embedded", "firmware", "vlsi", "rtos", "iot", "hardware engineer"]),
    (
        "hr",
        [
            "hrbp",
            "hr ",
            "human resources",
            "talent acquisition",
            "recruiter",
            "people partner",
        ],
    ),
    ("sales", ["sales", "business development", "account executive"]),
    ("supply_chain", ["supply chain", "procurement", "logistics", "warehouse"]),
    ("project_manager", ["project manager", "program manager", "delivery manager"]),
    ("technical_support", ["technical support", "it support", "helpdesk", "help desk"]),
    ("data", ["data analyst", "data scientist", "data engineer", "analytics"]),
    ("finance", ["finance", "accountant", "accounting", "auditor"]),
    (
        "software",
        ["software engineer", "developer", "full stack", "backend", "frontend"],
    ),
]

ROLE_SKILL_SUGGESTIONS = {
    "embedded": [
        "Embedded C",
        "RTOS",
        "Device Drivers",
        "ARM Architecture",
        "I2C",
        "SPI",
        "Board Bring-up",
    ],
    "hr": [
        "Talent Acquisition",
        "Employee Relations",
        "HRIS",
        "Performance Management",
        "Stakeholder Management",
    ],
    "sales": [
        "CRM",
        "Lead Generation",
        "Negotiation",
        "Account Management",
        "Market Research",
    ],
    "supply_chain": [
        "Vendor Management",
        "Inventory Management",
        "ERP",
        "SAP",
        "Demand Planning",
    ],
    "project_manager": [
        "Risk Management",
        "Stakeholder Communication",
        "Budgeting",
        "Agile",
        "Roadmap Planning",
    ],
    "technical_support": [
        "Troubleshooting",
        "Ticketing Systems",
        "IT Infrastructure",
        "Networking",
        "ITIL",
    ],
    "data": ["SQL", "Data Visualization", "Pandas", "Power BI", "Data Analysis"],
    "finance": [
        "Financial Analysis",
        "Budgeting",
        "Forecasting",
        "Excel",
        "Financial Modeling",
    ],
    "software": ["Git", "REST API", "CI/CD", "Unit Testing", "System Design"],
}

KNOWN_CITIES = [
    "Bengaluru",
    "Bangalore",
    "Gurugram",
    "Gurgaon",
    "Delhi",
    "New Delhi",
    # "Mumbai",
    # "Pune",
    # "Hyderabad",
    # "Chennai",
    # "Noida",
    # "Kolkata",
    "Remote",
]

DESCRIPTION_HEADINGS = [
    "responsibilities",
    "key responsibilities",
    "role overview",
    "about the role",
    "job summary",
    "job description",
    "what you'll do",
    "overview",
    "role summary",
]

REQUIREMENTS_HEADINGS = [
    "requirements",
    "qualifications",
    "what you'll need",
    "skills required",
    "eligibility",
    "must have",
    "preferred qualifications",
    "who you are",
]

EMPLOYMENT_TYPE_PATTERNS = [
    (r"\bintern(ship)?\b", "intern"),
    (r"\bpart[\s-]?time\b", "part_time"),
    (r"\bcontract(or)?\b", "contract"),
    (r"\bfull[\s-]?time\b", "full_time"),
]

EXPERIENCE_PATTERNS = [
    re.compile(r"(\d{1,2})\s*(?:\+)?\s*(?:to|-|–|—)\s*(\d{1,2})\s*\+?\s*years", re.IGNORECASE),
    re.compile(r"minimum\s+(?:of\s+)?(\d{1,2})\s*\+?\s*years", re.IGNORECASE),
    re.compile(r"at\s+least\s+(\d{1,2})\s*\+?\s*years", re.IGNORECASE),
    re.compile(r"(\d{1,2})\s*\+\s*years", re.IGNORECASE),
    re.compile(r"(\d{1,2})\s*years?\s+of\s+experience", re.IGNORECASE),
]


def _detect_employment_type(text: str) -> str:
    lowered = text.lower()
    for pattern, value in EMPLOYMENT_TYPE_PATTERNS:
        if re.search(pattern, lowered):
            return value
    return "full_time"


def _detect_experience_years(text: str):
    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 2:
            low, high = int(groups[0]), int(groups[1])
            return min(low, high), max(low, high)
        value = int(groups[0])
        return value, value
    return 0, 0


def _detect_location(text: str) -> str:
    match = re.search(r"location\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if match:
        candidate = match.group(1).strip().splitlines()[0]
        if candidate:
            return candidate[:150]
    lowered = text.lower()
    for city in KNOWN_CITIES:
        if city.lower() in lowered:
            return city
    return ""


def _detect_title(text: str) -> str:
    for pattern in (
        r"job\s*title\s*[:\-]\s*(.+)",
        r"position\s*[:\-]\s*(.+)",
        r"role\s*[:\-]\s*(.+)",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip().splitlines()[0]
            if candidate:
                return candidate[:255]
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:255]
    return ""


def _detect_department(text: str) -> str:
    match = re.search(r"department\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().splitlines()[0][:100]
    return ""


def _is_heading_line(line: str, keywords) -> bool:
    cleaned = line.strip().lstrip("#").strip().rstrip(":").strip().lower()
    if not cleaned or len(cleaned) > 60:
        return False
    return any(keyword in cleaned for keyword in keywords)


def _split_sections(text: str):
    lines = text.splitlines()
    description_lines = []
    requirements_lines = []
    current = None

    for line in lines:
        if _is_heading_line(line, DESCRIPTION_HEADINGS):
            current = "description"
            continue
        if _is_heading_line(line, REQUIREMENTS_HEADINGS):
            current = "requirements"
            continue
        if current == "description":
            description_lines.append(line)
        elif current == "requirements":
            requirements_lines.append(line)

    description = "\n".join(description_lines).strip()
    requirements = "\n".join(requirements_lines).strip()

    if not description and not requirements:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        midpoint = max(1, len(paragraphs) // 2)
        description = "\n\n".join(paragraphs[:midpoint])
        requirements = "\n\n".join(paragraphs[midpoint:])

    return description, requirements


def _clean_description(text: str, max_sentences: int = 7) -> str:
    text = re.sub(r"[#*_>`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:max_sentences]).strip()


def _clean_requirements(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        line = re.sub(r"^[#*_>`]+", "", line).strip()
        line = re.sub(r"^[-*•]\s*", "", line).strip()
        if not line:
            continue
        cleaned.append(f"- {line}")
    return "\n".join(cleaned[:20])


def _extract_skills(text: str, title: str):
    keyword_processor = KeywordProcessor(case_sensitive=False)
    for skill in SKILLS_VOCAB:
        keyword_processor.add_keyword(skill)

    found = keyword_processor.extract_keywords(text)
    deduped = []
    seen = set()
    for skill in found:
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(skill)

    title_lower = title.lower()
    for category, keywords in ROLE_CATEGORY_KEYWORDS:
        if any(keyword in title_lower for keyword in keywords):
            for suggestion in ROLE_SKILL_SUGGESTIONS.get(category, []):
                key = suggestion.lower()
                if key not in seen:
                    seen.add(key)
                    deduped.append(suggestion)
            break

    return deduped


def extract_job_fields(markdown_text: str) -> dict:
    """
    Fully local, offline extraction. No network calls, no API key, no rate
    limits. Extracts what is actually present in the document via regex and
    keyword matching; adds a bounded, clearly-heuristic set of role-typical
    skills based on detected job category (not AI-generated, a static
    lookup table — see ROLE_SKILL_SUGGESTIONS above).
    """
    if not markdown_text or not markdown_text.strip():
        raise ExtractionError("No text was available to extract job details from.")

    title = _detect_title(markdown_text)
    department = _detect_department(markdown_text)
    location = _detect_location(markdown_text)
    employment_type = _detect_employment_type(markdown_text)
    exp_min, exp_max = _detect_experience_years(markdown_text)

    description_raw, requirements_raw = _split_sections(markdown_text)
    description = _clean_description(description_raw)
    requirements = _clean_requirements(requirements_raw)

    skills = _extract_skills(markdown_text, title)

    return {
        "title": title,
        "department": department,
        "location": location,
        "employment_type": employment_type,
        "experience_min_years": exp_min,
        "experience_max_years": exp_max,
        "skills": skills,
        "description": description,
        "requirements": requirements,
    }
