from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import csv
import re
import logging
from pathlib import Path
from difflib import get_close_matches
from openai import OpenAI

app = FastAPI()

LOG_PATH = Path(__file__).resolve().parent / "backend.log"


def _configure_file_logging() -> None:
    """Write backend runtime logs to backend.log for easier debugging in editor."""
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "backend"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        # Avoid duplicate handlers on reload.
        if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(LOG_PATH) for h in logger.handlers):
            logger.addHandler(file_handler)
        if logger_name in {"uvicorn.error", "uvicorn.access", "backend"}:
            logger.propagate = False


_configure_file_logging()
logger = logging.getLogger("backend")

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for goals
goals = []

# In-memory downstream artifact for post-processing pipelines.
downstream_object = {
    "major": "",
    "keywords": [],
    "major_keywords_concat": "",
}

class Goal(BaseModel):
    text: str

# Load available majors from CSV
def load_majors(csv_path: str) -> List[str]:
    majors = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if not row:
                    continue
                title = row[0].strip()
                if title:
                    majors.append(title)
    except FileNotFoundError:
        print(f"Majors file not found: {csv_path}")
    return majors

MAJORS_LIST = load_majors(Path(__file__).resolve().parents[1] / 'Majors.csv')

# Initialize OpenAI client (optional)
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

def suggest_major(goals_list):
    if not goals_list:
        return "Undecided"

    goals_text = "\n".join(goals_list)
    majors_text = ", ".join(MAJORS_LIST[:50])  # show subset to reduce prompt length
    prompt = (
        "Based on these goals, suggest the most relevant college major from the list provided. "
        "Respond with exactly one major name from the list. "
        f"Majors: {majors_text}\n\n"
        f"Goals:\n{goals_text}\n"
    )

    # Deterministic fallback scoring that does not require OpenAI.
    def fallback_major() -> str:
        text = goals_text.lower()
        tokens = re.findall(r"\w+", text)

        # Broad domain intent hints (general-purpose, not prompt-specific).
        intent_hints = {
            "Computer Science": {"software", "coding", "programming", "developer", "engineer", "technology", "tech", "computer", "ai", "data", "google", "microsoft", "meta", "amazon", "apple", "nvidia", "openai", "tesla"},
            "Business": {"business", "management", "leader", "leadership", "finance", "economics", "company", "startup", "market", "global", "travel", "policy", "senator", "government", "politics", "political", "public", "diplomacy", "law"},
            "Engineering": {"engineering", "design", "build", "hardware", "systems", "mechanical", "electrical", "infrastructure"},
            "Biology": {"biology", "medical", "medicine", "health", "genetics", "biochem", "lab", "organism"},
            "Psychology": {"psychology", "mental", "behavior", "social", "people", "counseling", "therapy"},
        }

        hint_scores = {m: 0 for m in majors_info.keys()}
        for major_name, hints in intent_hints.items():
            hint_scores[major_name] = sum(1 for t in tokens if t in hints)

        hinted_major = max(hint_scores, key=hint_scores.get)
        if hint_scores[hinted_major] > 0:
            return hinted_major

        score_map = {m: 0 for m in majors_info.keys()}

        for major_name, info in majors_info.items():
            major_lower = major_name.lower()
            if major_lower in text:
                score_map[major_name] += 3

            for job in info.get("jobs", []):
                for token in job.lower().split():
                    if len(token) >= 4 and token in text:
                        score_map[major_name] += 2

            for skill in info.get("skills", []):
                for token in skill.lower().split():
                    if len(token) >= 4 and token in text:
                        score_map[major_name] += 1

        best_major = max(score_map, key=score_map.get)
        # Never return Undecided in fallback; use a neutral default major when no signal exists.
        return best_major if score_map[best_major] > 0 else "Business"

    if not client:
        return fallback_major()

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        suggested = response.choices[0].message.content.strip()

        # Attempt to match suggested name to the known majors list
        if suggested in MAJORS_LIST:
            return suggested

        # Fuzzy match fallback
        matches = get_close_matches(suggested, MAJORS_LIST, n=1, cutoff=0.6)
        if matches:
            return matches[0]

        return fallback_major()
    except Exception as e:
        print(f"Error with OpenAI: {e}")
        return fallback_major()

# Electives and skills mapping based on major + high-level job roles
majors_info = {
    "Computer Science": {
        "jobs": ["Software Engineer", "Data Scientist", "Systems Architect"],
        "skills": [
            "programming", "algorithms", "data structures", "databases", "machine learning",
            "software design", "systems", "computational thinking"
        ],
        "electives": [
            "Advanced Algorithms", "Databases", "Machine Learning", "Operating Systems", "Software Engineering"
        ],
    },
    "Business": {
        "jobs": ["Business Analyst", "Product Manager", "Marketing Manager"],
        "skills": [
            "analysis", "strategy", "marketing", "finance", "leadership", "communication"
        ],
        "electives": [
            "Marketing Strategy", "Financial Modeling", "Product Management", "Organizational Behavior", "Entrepreneurship"
        ],
    },
    "Engineering": {
        "jobs": ["Mechanical Engineer", "Electrical Engineer", "Civil Engineer"],
        "skills": [
            "design", "problem solving", "math", "physics", "materials", "systems"
        ],
        "electives": [
            "Engineering Design", "Control Systems", "Thermodynamics", "Structural Analysis", "Embedded Systems"
        ],
    },
    "Biology": {
        "jobs": ["Biotechnologist", "Research Scientist", "Healthcare Specialist"],
        "skills": [
            "laboratory", "research", "genetics", "cell biology", "biochemistry"
        ],
        "electives": [
            "Genetics", "Microbiology", "Biochemistry", "Molecular Biology", "Bioinformatics"
        ],
    },
    "Psychology": {
        "jobs": ["Clinical Psychologist", "Counselor", "User Researcher"],
        "skills": [
            "human behavior", "research", "communication", "counseling", "analysis"
        ],
        "electives": [
            "Research Methods", "Cognitive Psychology", "Social Psychology", "Counseling Techniques", "Human Factors"
        ],
    },
}

stopwords = {
    "a", "an", "the", "and", "or", "but", "to", "for", "with", "on", "in", "at", "of", "by",
    "from", "about", "as", "is", "are", "it", "this", "that", "these", "those", "my", "i", "me",
    "you", "your", "we", "our", "us", "be", "will", "can", "want", "would", "could", "should",
}


def llm_extract_keywords(goals_list):
    """Use the LLM to infer relevant keywords from the user's goals."""
    if not goals_list:
        return []

    goals_text = "\n".join(goals_list)
    prompt = (
        "Extract 5-10 keywords or short phrases that represent important skills, topics, or domains "
        "from these career goals. Respond with a comma-separated list only.\n\n"
        f"Goals:\n{goals_text}\n"
    )

    if not client:
        return []

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
        )
        raw = response.choices[0].message.content.strip()
        # parse comma-separated output
        keywords = [k.strip().lower() for k in raw.split(',') if k.strip()]
        # filter stopwords and dedupe while preserving order
        seen = set()
        filtered = []
        for kw in keywords:
            kw = kw.strip().strip('"')
            if not kw or kw in stopwords or kw in seen:
                continue
            seen.add(kw)
            filtered.append(kw)
        return filtered
    except Exception as e:
        print(f"Error extracting keywords with OpenAI: {e}")
        return []


def extract_keywords(goals_list):
    keywords = llm_extract_keywords(goals_list)
    if keywords:
        return keywords

    # Fallback: simple tokenization
    if not goals_list:
        return []
    text = " ".join(goals_list).lower()
    words = [w.strip(".,!?;:\"()[]") for w in text.split()]
    keywords = [w for w in words if w and w not in stopwords]
    # keep unique, preserve order
    seen = set()
    result = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            result.append(w)
    return result

def suggest_electives(major, keywords):
    info = majors_info.get(major)
    if not info:
        return {"major": major, "keywords": keywords, "electives": []}

    # pick electives that match any extracted keyword / skill
    matched = [e for e in info["electives"] if any(k in e.lower() for k in keywords)]
    if not matched:
        matched = info["electives"]

    return {
        "major": major,
        "jobs": info["jobs"],
        "keywords": keywords,
        "electives": matched,
    }

@app.get("/goals", response_model=List[str])
async def get_goals():
    return goals

@app.post("/goals")
async def add_goal(goal: Goal):
    # Keep only the latest goal so each submission is independent.
    goals.clear()
    goals.append(goal.text)
    # Extract keywords from the latest submitted goal only
    keywords = extract_keywords([goal.text])
    suggested_major = suggest_major([goal.text])

    # Ensure keywords are useful and related to the selected major.
    if suggested_major in majors_info:
        major_skills = [s.lower() for s in majors_info[suggested_major].get("skills", [])]
        merged = []
        for k in keywords + major_skills:
            k = k.lower()
            if k not in stopwords and k not in merged:
                merged.append(k)
            if len(merged) >= 5:
                break
        keywords = merged

    electives_info = suggest_electives(suggested_major, keywords)

    # Concatenate major + related keywords for downstream processing.
    downstream_object["major"] = suggested_major
    downstream_object["keywords"] = keywords
    downstream_object["major_keywords_concat"] = f"{suggested_major}: {', '.join(keywords)}"

    logger.info("Goal processed: text=%r major=%s keywords=%s", goal.text, suggested_major, keywords)
    return {
        "message": "Goal added successfully",
        "suggested_major": suggested_major,
        "keywords": keywords,
        "electives": electives_info,
        "downstream_object": downstream_object,
    }


@app.get("/downstream-object")
async def get_downstream_object():
    return downstream_object

@app.get("/plan")
async def get_plan():
    if not goals:
        return {"error": "No goals available"}
    
    # Simple computation: distribute goals across 8 semesters
    plan = []
    for i in range(8):
        semester_goals = goals[i % len(goals): (i+1) % len(goals) or None] if goals else []
        plan.append({
            "semester": f"Semester {i+1}",
            "goals": semester_goals,
            "description": f"Focus on {', '.join(semester_goals[:2])} and more." if semester_goals else "No specific goals for this semester."
        })
    return plan

@app.get("/electives")
async def get_electives():
    if not goals:
        return {"error": "No goals available"}

    latest_goal = [goals[-1]]
    keywords = extract_keywords(latest_goal)
    suggested_major = suggest_major(latest_goal)
    electives_info = suggest_electives(suggested_major, keywords)

    return {
        "major": suggested_major,
        "keywords": keywords,
        "electives": electives_info,
    }
