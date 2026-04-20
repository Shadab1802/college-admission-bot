"""
screening_service.py

Auto-screens a student application:
1. Fetch student's extracted marks from DB
2. Fetch eligibility criteria from pgvector (RAG search)
3. Ask Groq to evaluate: selected / rejected / borderline
4. Store decision + reasoning in application record
"""
import os
import json
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.db_models import Application, Document, Course, ApplicationStatus
from services.doc_parser import embed_query

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL  = "llama-3.1-8b-instant"


# ── Fetch eligibility context from pgvector ────────────────

def get_eligibility_context(db: Session, course_type: str) -> str:
    """Search college docs for eligibility criteria relevant to UG or PG"""
    query    = f"eligibility criteria admission requirements {course_type}"
    embedding = embed_query(query)

    result = db.execute(
        text("""
            SELECT chunk_text
            FROM doc_chunks
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT 6
        """),
        {"embedding": str(embedding)}
    )
    chunks = [row[0] for row in result.fetchall()]
    return "\n\n".join(chunks) if chunks else "No eligibility criteria found in documents."


# ── Main screening function ────────────────────────────────

def screen_application(db: Session, application_id: int) -> dict:
    """
    Evaluates one application.
    Returns: {"status": "auto_selected"|"auto_rejected"|"borderline", "notes": "..."}
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        return {"status": "pending", "notes": "Application not found"}

    course = db.query(Course).filter(Course.id == application.course_id).first()

    # ── Get student's marksheet data ───────────────────────
    doc_type = "marksheet_12th" if course.type == "UG" else "marksheet_btech"
    document = (
        db.query(Document)
        .filter(
            Document.student_id == application.student_id,
            Document.type == doc_type
        )
        .order_by(Document.uploaded_at.desc())
        .first()
    )

    if not document or not document.extracted_marks:
        # Can't screen without marks — mark as pending
        application.screening_notes = "Awaiting marksheet upload for screening."
        db.commit()
        return {"status": "pending", "notes": application.screening_notes}

    marks_info = json.dumps(document.extracted_marks)

    # ── Get eligibility criteria from college docs ─────────
    eligibility_context = get_eligibility_context(db, course.type)

    # ── Ask Groq to evaluate ───────────────────────────────
    prompt = f"""You are an admissions screening assistant. Evaluate this student's eligibility.

Course Applied: {course.name} ({course.type})

Student's Academic Record:
{marks_info}

Eligibility Criteria from College Documents:
{eligibility_context}

Task:
1. Check if the student meets the eligibility criteria
2. Consider a 2% margin as "borderline" (e.g., if cutoff is 60% and student has 58-60%)
3. Respond ONLY in this exact JSON format, no extra text:

{{
  "decision": "auto_selected" | "auto_rejected" | "borderline",
  "reasoning": "One clear sentence explaining why",
  "percentage_found": <number or null>,
  "cutoff_found": <number or null>
}}
"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,    # low temp for consistent structured output
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()

    # ── Parse Groq's JSON response ─────────────────────────
    try:
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        decision  = result.get("decision", "borderline")
        reasoning = result.get("reasoning", "Could not determine eligibility.")
    except (json.JSONDecodeError, KeyError):
        decision  = "borderline"
        reasoning = f"Auto-screening inconclusive. Raw response: {raw[:200]}"

    # ── Persist decision ───────────────────────────────────
    application.status          = ApplicationStatus(decision)
    application.screening_notes = reasoning
    db.commit()

    return {"status": decision, "notes": reasoning}


# ── Batch screen all pending applications ─────────────────

def screen_all_pending(db: Session) -> dict:
    """Screen all applications that are still in 'pending' state"""
    pending = db.query(Application).filter(
        Application.status == ApplicationStatus.pending
    ).all()

    results = {"auto_selected": 0, "auto_rejected": 0, "borderline": 0, "pending": 0}

    for app in pending:
        result = screen_application(db, app.id)
        status = result.get("status", "pending")
        if status in results:
            results[status] += 1

    return {"screened": len(pending), "breakdown": results}