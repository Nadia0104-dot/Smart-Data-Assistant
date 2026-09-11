# backend/engine.py

from flask import Flask, request, jsonify, Response, stream_with_context
from simplyhired import SimplyHiredScraper

import json, re
from collections import Counter

app = Flask(__name__)

# ================= UTIL =================
def extract_skills(text):
    if not text:
        return []

    text = text.lower()
    patterns = {
        "python": r"\bpython\b",
        "sql": r"\bsql\b",
        "aws": r"\baws|amazon web services\b",
        "react": r"\breact\b",
        "node": r"\bnode(\.js)?\b",
        "docker": r"\bdocker\b",
        "kubernetes": r"\bkubernetes|k8s\b",
        "java": r"\bjava\b",
        "c++": r"\bc\+\+\b",
        "javascript": r"\bjavascript|js\b",
        "typescript": r"\btypescript|ts\b",
        "mongodb": r"\bmongodb\b",
        "firebase": r"\bfirebase\b",
        "unity": r"\bunity\b",
        "c#": r"\bc#|csharp\b",
        "ai": r"\bartificial intelligence\b",
        "ml": r"\bmachine learning\b"
    }

    return [skill for skill, pattern in patterns.items() if re.search(pattern, text)]


# ================= SKILL MATCHING & JOB ENRICHMENT =================
def calculate_match(job, resume_skills):
    """Weighted skill match score (0-100)."""
    if not resume_skills:
        return 0

    job_text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        " ".join(job.get("skills", []))
    ]).lower()

    exact = sum(3 for s in resume_skills if s.lower() in job_text)
    partial = sum(1.5 for s in resume_skills if s.lower()[:3] in job_text)
    total_possible = len(resume_skills) * 3

    return round(min(100, (exact / total_possible) * 100)) if total_possible else 0


def skill_gap(job, resume_skills):
    """Returns skills in job not present in resume."""
    return list(set(job.get("skills", [])) - set(resume_skills))


def estimate_salary(job):
    if job.get("salary"):
        return job["salary"]
    title = (job.get("title") or "").lower()
    base = 40000
    if "senior" in title: base += 40000
    elif "junior" in title: base += 10000
    else: base += 25000
    return f"${base} - ${base + 20000}"


def enrich_job(job, resume_skills):
    """Enrich a single job with skills, score, gap, salary."""
    job_text = job.get("description") or job.get("snippet") or ""
    if not job.get("skills"):
        job["skills"] = extract_skills(job_text)

    job["score"] = calculate_match(job, resume_skills)
    job["skill_gap"] = skill_gap(job, resume_skills)
    job["salary_estimate"] = estimate_salary(job)
    return job


# ================= STREAM SCRAPER =================
@app.route("/api/simplyhired", methods=["GET"])
def stream_jobs():
    job = request.args.get("job")
    location = request.args.get("location")
    full = request.args.get("full", "false").lower() == "true"

    def generate():
        scraper = SimplyHiredScraper(headless=True)
        try:
            for step in scraper.scrape_stream(job, location, full, 1):
                yield f"data: {json.dumps({'log': step})}\n\n"
        finally:
            scraper.close()

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ================= EDUCATION =================
EDU_KEYWORDS = {
    "bachelor": ["bachelor", "bs", "b.sc"],
    "master": ["master", "ms", "m.sc"],
    "phd": ["phd"]
}


# ================= RESUME ANALYZER =================
@app.route("/api/analyze_resume", methods=["POST"])
def analyze_resume():
    if 'resume' not in request.files:
        return jsonify({"error": "No resume uploaded"}), 400

    file = request.files['resume']
    filename = file.filename.lower()
    text = ""

    try:
        if filename.endswith(".txt"):
            text = file.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(file) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        elif filename.endswith(".docx"):
            from docx import Document
            doc = Document(file)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif filename.endswith(".doc"):
            text = file.read().decode("latin-1", errors="ignore")
        else:
            return jsonify({"error": "Unsupported file type"}), 400
    except Exception as e:
        return jsonify({"error": f"Parsing failed: {str(e)}"}), 500

    # ================= CLEAN TEXT =================
    text = re.sub(r'(\b\w\s)+\w\b', lambda m: m.group(0).replace(" ", ""), text)
    text = re.sub(r'\s+', ' ', text).lower()

    # ================= SKILL KB =================
    SKILL_KB = {
        "react": ["react"], "node.js": ["node", "nodejs"],
        "python": ["python"], "sql": ["sql"],
        "power bi": ["power bi"], "excel": ["excel"],
        "postgresql": ["postgresql", "postgres"],
        "plotly": ["plotly"], "matplotlib": ["matplotlib"],
        "web scraping": ["scraping"], "api": ["api"],
        "machine learning": ["ml"],
        "unity": ["unity"], "c#": ["c#", "csharp"],
        "lead generation": ["lead"], "linkedin": ["linkedin"]
    }

    # ================= INTELLIGENT SKILL EXTRACTION =================
    skills_with_score = {}
    for skill, aliases in SKILL_KB.items():
        total_score = 0
        for alias in aliases:
            occurrences = len(re.findall(rf"\b{re.escape(alias)}\b", text))
            if occurrences:
                score = 1 + (occurrences * 0.5)
                if "skill" in text: score += 1
                if "experience" in text: score += 0.5
                if "project" in text: score += 0.7
                total_score += score
        if total_score > 0:
            skills_with_score[skill] = round(total_score, 2)

    skills_found = list(skills_with_score.keys())

    # ================= CATEGORY MAP =================
    CATEGORY_MAP = {
        "frontend": ["react"],
        "backend": ["node.js", "api"],
        "data": ["python", "sql", "power bi", "excel"],
        "database": ["postgresql"],
        "game_dev": ["unity", "c#"],
        "scraping": ["web scraping"],
        "business": ["lead generation", "linkedin"]
    }

    categories = {k: [s for s in skills_found if s in v] for k, v in CATEGORY_MAP.items() if any(s in v for s in skills_found)}

    # ================= EXPERIENCE =================
    exp_matches = re.findall(r"(\d+)\+?\s+years", text)
    experience_years = max([int(x) for x in exp_matches], default=0)

    # ================= EDUCATION =================
    education = [level for level, kws in EDU_KEYWORDS.items() if any(kw in text for kw in kws)]

    # ================= ROLE DETECTION =================
    ROLE_MAP = {
        "Data Analyst": ["python", "sql", "power bi"],
        "Frontend Developer": ["react"],
        "Backend Developer": ["node.js"],
        "Game Developer": ["unity"],
    }

    role_scores = {role: round(sum(skills_with_score.get(s, 0) for s in req_skills), 2)
                   for role, req_skills in ROLE_MAP.items() if any(skills_with_score.get(s, 0) for s in req_skills)}

    roles = sorted(role_scores, key=role_scores.get, reverse=True)

    # ================= FINAL SCORE =================
    strength_score = min(100, int(sum(skills_with_score.values()) * 5))

    return jsonify({
        "skills": skills_found,
        "skill_scores": skills_with_score,
        "categories": categories,
        "roles": roles,
        "role_scores": role_scores,
        "experience_years": experience_years,
        "education": education,
        "strength_score": strength_score,
        "total_skills": len(skills_found)
    })


# ================= JOB ENRICHMENT =================
@app.route("/api/enrich_jobs", methods=["POST"])
def enrich_jobs():
    data = request.json
    jobs = data.get("jobs", [])
    resume_skills = data.get("resume_skills", [])
    enriched = [enrich_job(job, resume_skills) for job in jobs]
    return jsonify({"jobs": enriched})


# ================= HEALTH =================
@app.route("/api/health")
def health():
    return {"status": "ok"}


# ================= AI INSIGHTS =================
@app.route("/api/ai_insight", methods=["POST"])
def ai_insight_api():
    jobs = request.json.get("jobs", [])
    if not jobs:
        return jsonify({"insight": "No jobs to analyze"})

    skill_counter = Counter()
    role_counter = Counter()

    ROLE_MAP = {
        "Data Analyst": ["python", "sql", "power bi", "excel"],
        "Frontend Developer": ["react", "javascript", "typescript", "html", "css"],
        "Backend Developer": ["node.js", "django", "flask", "api"],
        "ML Engineer": ["machine learning", "deep learning", "python"],
        "Game Developer": ["unity", "c#"],
    }

    for job in jobs:
        for s in job.get("skills", []):
            skill_counter[s] += 1
        for role, skills in ROLE_MAP.items():
            if any(sk in job.get("skills", []) for sk in skills):
                role_counter[role] += 1

    top_skills = [s[0] for s in skill_counter.most_common(5)]
    top_roles = [r[0] for r in role_counter.most_common(3)]

    insight_text = f"🔥 Trending skills: {', '.join(top_skills)}"
    if top_roles:
        insight_text += f"\n💼 Emerging roles: {', '.join(top_roles)}"

    return jsonify({"insight": insight_text})


# ================= DASHBOARD =================
@app.route("/api/dashboard", methods=["POST"])
def dashboard_api():
    jobs = request.json.get("jobs", [])
    skill_counter = Counter()
    company_counter = Counter()
    location_counter = Counter()

    for j in jobs:
        for s in j.get("skills", []):
            skill_counter[s] += 1
        if j.get("company"):
            company_counter[j["company"]] += 1
        if j.get("location"):
            location_counter[j["location"]] += 1

    return jsonify({
        "skills": skill_counter.most_common(10),
        "companies": company_counter.most_common(5),
        "locations": location_counter.most_common(5)
    })