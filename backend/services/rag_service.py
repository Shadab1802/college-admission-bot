"""
rag_service.py
Handles:
  - pgvector similarity search for relevant chunks
  - Building role-aware system prompts
  - Streaming Groq response (llama3)
"""
import os
from typing import AsyncGenerator, Optional
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import text

from services.doc_parser import embed_query
from models.db_models import User, Application, ExamSchedule, Course

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL  = "llama-3.1-8b-instant"   # fast, free tier friendly


# ── Vector Search ──────────────────────────────────────────

def search_relevant_chunks(db: Session, query: str, top_k: int = 5) -> list[str]:
    """
    Embeds the query and finds top_k most similar chunks using pgvector cosine similarity.
    """
    query_embedding = embed_query(query)

    # pgvector cosine similarity via raw SQL (SQLAlchemy doesn't wrap this natively)
    result = db.execute(
        text("""
            SELECT chunk_text
            FROM doc_chunks
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """),
        {"embedding": str(query_embedding), "top_k": top_k}
    )
    return [row[0] for row in result.fetchall()]


# ── System Prompt Builder ──────────────────────────────────

def build_student_system_prompt(db: Session, user: User) -> str:
    """Inject student's profile + application status into Aria's context"""

    application = (
        db.query(Application)
        .filter(Application.student_id == user.id)
        .order_by(Application.created_at.desc())
        .first()
    )

    profile_context = f"Student Name: {user.name}\nEmail: {user.email}\n"

    if application:
        course = db.query(Course).filter(Course.id == application.course_id).first()
        profile_context += f"Applied Course: {course.name} ({course.type})\n"
        profile_context += f"Application Status: {application.status}\n"

        schedule = db.query(ExamSchedule).filter(
            ExamSchedule.course_id == application.course_id
        ).first()

        if schedule and application.status in ("selected", "auto_selected"):
            profile_context += f"Exam Date: {schedule.exam_date}\n"
            profile_context += f"Venue: {schedule.venue}\n"
    else:
        profile_context += "Application Status: Not yet applied\n"

    # Add available courses so Aria knows the IDs for [ACTION:apply_course:ID]
    courses = db.query(Course).all()
    if courses:
        profile_context += "\nAvailable Courses for Application (ID: Name):\n"
        for c in courses:
            profile_context += f"- {c.id}: {c.name} ({c.type})\n"

    return f"""You are Aria, a warm, friendly and professional admissions assistant for this college.
You help students with queries about admissions, courses, fees, eligibility, and exam details.

Current Student Profile:
{profile_context}

Rules:
- Answer ONLY using the provided college document context below.
- If the answer is not in the context, say "I don't have that information right now, please contact the admissions office."
- Be concise, friendly, and helpful. Use the student's name naturally.
- Never make up fees, dates, or eligibility criteria.
- If the student HAS applied and needs to upload their marksheet, ask them to upload it right here using the button below. (To show the upload button, include the marker **[UPLOAD_MARKSHEET]** at the end of your message). NEVER show this button if the student hasn't applied yet.
- Never expose admission statistics, aggregate numbers of applicants, or any data about other students.
- If the student has NOT applied yet and seems ready, you can offer an 'Apply Now' button in the chat ONLY IF you see numeric Course IDs in the profile context above. Include **[ACTION:apply_course:COURSE_ID]** in your message (replace COURSE_ID with the numeric ID).
- If no courses are listed in your context or if you are unsure of the ID, guide them to the **My Application** dashboard to choose a course manually.
"""


def build_director_system_prompt(db: Session, user: User) -> str:
    """Director mode — Aria acts as an admin analytics assistant"""

    # Quick stats snapshot
    from models.db_models import Application, ApplicationStatus
    from sqlalchemy import func

    total    = db.query(func.count(Application.id)).scalar() or 0
    selected = db.query(func.count(Application.id)).filter(
        Application.status.in_(["selected", "auto_selected"])
    ).scalar() or 0
    pending  = db.query(func.count(Application.id)).filter(
        Application.status == "pending"
    ).scalar() or 0
    rejected = db.query(func.count(Application.id)).filter(
        Application.status.in_(["rejected", "auto_rejected"])
    ).scalar() or 0

    return f"""You are Aria, the intelligent admin assistant for the college admissions portal.
You assist the director with insights, statistics, and queries about the admission process.

Live Snapshot:
- Total Applications: {total}
- Selected: {selected}
- Pending Screening: {pending}
- Rejected: {rejected}

Director: {user.name}

Capabilities:
- Answer questions about applicant statistics naturally
- Help interpret admission trends
- Answer questions about the college's own uploaded documents
- If asked for data you can't compute, suggest checking the dashboard

Rules:
- Be professional but conversational
- Always ground answers in real data when possible
- Never reveal individual student passwords or sensitive personal data
"""


# ── Main Chat Function (Streaming) ─────────────────────────

async def stream_chat_response(
    db: Session,
    user: User,
    user_message: str,
    chat_history: list[dict]
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline:
    1. Search relevant chunks from college docs
    2. Build role-aware system prompt
    3. Stream Groq response token by token
    """

    # Step 1: Get relevant context from college docs
    context_chunks = search_relevant_chunks(db, user_message, top_k=5)
    context_text   = "\n\n---\n\n".join(context_chunks) if context_chunks else "No relevant documents found."

    # Step 2: Build system prompt based on role
    if user.role == "director":
        system_prompt = build_director_system_prompt(db, user)
    else:
        system_prompt = build_student_system_prompt(db, user)

    # Append retrieved context to system prompt
    system_prompt += f"\n\n=== Relevant College Document Excerpts ===\n{context_text}"

    # Step 3: Build message list (history + current)
    messages = [{"role": "system", "content": system_prompt}]
    messages += chat_history[-10:]   # keep last 10 turns for context window efficiency
    messages.append({"role": "user", "content": user_message})

    # Step 4: Stream from Groq
    stream = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        stream=True,
        temperature=0.4,
        max_tokens=1024,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta