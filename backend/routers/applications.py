"""
applications.py router

GET    /applications/courses           → list all available courses
POST   /applications/apply             → student chooses a course
POST   /applications/upload-marksheet  → student uploads marksheet
DELETE /applications/delete-marksheet  → student deletes marksheet (to re-upload)
GET    /applications/my-documents      → list all student-uploaded documents
GET    /applications/my-status         → student checks their application status
"""
import os
import json
from pathlib import Path

import fitz                          # PyMuPDF — extract marks from PDF
import httpx
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db.database import get_db
from models.db_models import (
    User, Course, Application, Document,
    ApplicationStatus, DocumentType
)
from schemas.application_schemas import (
    ApplyRequest, ApplicationResponse, CourseResponse
)
from schemas.auth_schemas import TokenData
from core.security import get_current_user
from services.screening_service import screen_application

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

router = APIRouter(prefix="/applications", tags=["Applications"])


# ── Helper: resolve student user ──────────────────────────

def get_student(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Students only")
    return current_user


# ── GET /applications/courses ──────────────────────────────

@router.get("/courses", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db)):
    """Public — no auth needed. Lists all available courses."""
    return db.query(Course).all()


# ── POST /applications/apply ───────────────────────────────

@router.post("/apply")
def apply_for_course(
    payload: ApplyRequest,
    student: User = Depends(get_student),
    db: Session = Depends(get_db)
):
    # Check course exists
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Prevent duplicate application for same course
    existing = db.query(Application).filter(
        Application.student_id == student.id,
        Application.course_id  == payload.course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied for this course")

    # One application at a time
    any_existing = db.query(Application).filter(
        Application.student_id == student.id
    ).first()
    if any_existing:
        raise HTTPException(
            status_code=400,
            detail=f"You already applied for '{any_existing.course.name}'. Contact admissions to change."
        )

    application = Application(
        student_id = student.id,
        course_id  = payload.course_id,
        status     = ApplicationStatus.pending
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    doc_needed = "12th marksheet" if course.type == "UG" else "B.Tech marksheet"
    return {
        "message":        f"Successfully applied for {course.name}!",
        "application_id": application.id,
        "next_step":      f"Please upload your {doc_needed} to complete your application.",
        "upload_endpoint": "/applications/upload-marksheet"
    }


# ── Marks extractor (heuristic from PDF text) ─────────────

def extract_marks_from_pdf(file_bytes: bytes) -> dict:
    """
    Advanced extraction using Groq LLM to parse PDF text.
    """
    from services.doc_parser import extract_text_from_pdf, parse_marksheet_text_with_llm
    
    full_text = extract_text_from_pdf(file_bytes)
    result    = parse_marksheet_text_with_llm(full_text)
    
    # Simple fallback: if only CGPA is found, convert to percentage for screening
    if result.get("cgpa") and not result.get("percentage"):
        result["percentage"] = round(result["cgpa"] * 9.5, 2)
        
    return result


# ── POST /applications/upload-marksheet ───────────────────

@router.post("/upload-marksheet")
async def upload_marksheet(
    file: UploadFile = File(...),
    student: User = Depends(get_student),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.student_id == student.id
    ).first()
    if not application:
        raise HTTPException(status_code=400, detail="Please apply for a course first")

    if application.status in ("selected", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="Cannot change marksheet after the decision has been finalized."
        )

    course = db.query(Course).filter(Course.id == application.course_id).first()

    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF marksheets accepted")

    file_bytes = await file.read()

    # ── Upload to Supabase Storage (always upsert by student id) ──
    storage_filename = f"{student.id}_marksheet.pdf"
    upload_url       = f"{SUPABASE_URL}/storage/v1/object/marksheets/{storage_filename}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            upload_url,
            content=file_bytes,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type":  "application/pdf",
                "x-upsert":      "true"
            }
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Upload failed: {resp.text}")

    file_url = f"{SUPABASE_URL}/storage/v1/object/public/marksheets/{storage_filename}"

    extracted = extract_marks_from_pdf(file_bytes)

    doc_type     = DocumentType.marksheet_12th if course.type == "UG" else DocumentType.marksheet_btech
    existing_doc = db.query(Document).filter(
        Document.student_id == student.id,
        Document.type       == doc_type
    ).first()

    if existing_doc:
        existing_doc.file_url        = file_url
        existing_doc.extracted_marks = extracted
        db.commit()
    else:
        db.add(Document(
            student_id      = student.id,
            type            = doc_type,
            file_url        = file_url,
            extracted_marks = extracted
        ))
        db.commit()

    # Reset to pending and re-screen with new marks
    application.status = ApplicationStatus.pending
    db.commit()
    screening_result = screen_application(db, application.id)

    return {
        "message":         "Marksheet uploaded and screening complete.",
        "extracted_marks": extracted,
        "screening":       screening_result,
        "note":            "The director will review and finalize your result."
    }


# ── DELETE /applications/delete-marksheet ─────────────────

@router.delete("/delete-marksheet")
async def delete_marksheet(
    student: User = Depends(get_student),
    db: Session = Depends(get_db)
):
    """
    Deletes the student's marksheet and resets their application to pending
    so they can upload a corrected file.
    Blocked after director has finalized the decision.
    """
    application = db.query(Application).filter(
        Application.student_id == student.id
    ).first()
    if not application:
        raise HTTPException(status_code=400, detail="No application found")

    if application.status in ("selected", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete marksheet after the decision has been finalized."
        )

    course   = db.query(Course).filter(Course.id == application.course_id).first()
    doc_type = DocumentType.marksheet_12th if course.type == "UG" else DocumentType.marksheet_btech

    doc = db.query(Document).filter(
        Document.student_id == student.id,
        Document.type       == doc_type
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No marksheet found to delete")

    # ── Delete from Supabase Storage (best-effort) ─────────
    storage_filename = f"{student.id}_marksheet.pdf"
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.delete(
            f"{SUPABASE_URL}/storage/v1/object/marksheets/{storage_filename}",
            headers={"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
        )

    # ── Remove DB record + reset status ───────────────────
    db.delete(doc)
    application.status          = ApplicationStatus.pending
    application.screening_notes = "Marksheet deleted by student — awaiting re-upload."
    db.commit()

    return {"message": "Marksheet deleted. Upload a new one to resume screening."}


# ── GET /applications/my-documents ────────────────────────

@router.get("/my-documents")
def my_documents(
    student: User = Depends(get_student),
    db: Session = Depends(get_db)
):
    """Returns all documents uploaded by the current student."""
    docs = (
        db.query(Document)
        .filter(Document.student_id == student.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return [
        {
            "id":              d.id,
            "type":            d.type,
            "file_url":        d.file_url,
            "extracted_marks": d.extracted_marks,
            "uploaded_at":     d.uploaded_at,
        }
        for d in docs
    ]


# ── GET /applications/my-status ───────────────────────────

@router.get("/my-status")
def my_status(
    student: User = Depends(get_student),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.student_id == student.id
    ).first()

    if not application:
        return {"status": "not_applied", "message": "You haven't applied yet."}

    course = db.query(Course).filter(Course.id == application.course_id).first()

    from models.db_models import ExamSchedule
    schedule = db.query(ExamSchedule).filter(
        ExamSchedule.course_id == application.course_id
    ).first()

    doc_type      = "marksheet_12th" if course.type == "UG" else "marksheet_btech"
    has_marksheet = (
        db.query(Document)
        .filter(Document.student_id == student.id, Document.type == doc_type)
        .first()
    ) is not None

    response = {
        "application_id":  application.id,
        "course":          {"name": course.name, "type": course.type},
        "status":          application.status,
        "screening_notes": application.screening_notes,
        "applied_on":      application.created_at,
        "has_marksheet":   has_marksheet,
    }

    if application.status in ("selected", "auto_selected") and schedule:
        response["exam_details"] = {
            "exam_date": schedule.exam_date,
            "venue":     schedule.venue,
        }

    return response