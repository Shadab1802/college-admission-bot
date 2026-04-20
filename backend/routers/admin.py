
"""GET  /admin/applicants              → all applicants grouped by status bucket
    POST /admin/override                → director overrides bot's screening decision
POST /admin/exam-schedule           → set exam date, venue, result date per course
POST /admin/finalize                → lock decisions and trigger email job
GET  /admin/stats                   → quick stats for director dashboard
POST /admin/generate-admit-card/{id}→ generate + store admit card for a selected student

Course Management (director adds courses via form, NOT hardcoded):
POST /admin/courses                 → add a course
PUT  /admin/courses/{id}            → update a course
DELETE /admin/courses/{id}          → remove a course
"""
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
import httpx

from db.database import get_db
from models.db_models import (
    User, Application, Course, ExamSchedule,
    ApplicationStatus, CourseType, Document, DocumentType, Template, TemplateType
)
from schemas.application_schemas import (
    OverrideRequest, ExamScheduleRequest, ExamScheduleResponse
)
from schemas.auth_schemas import TokenData
from core.security import get_current_user
from services.screening_service import screen_all_pending
from services.email_service import (
    build_placeholders, fill_docx_template, convert_docx_to_pdf,
    generate_roll_number, fetch_template_bytes
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Helper: resolve director ───────────────────────────────

def get_director(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "director":
        raise HTTPException(status_code=403, detail="Director access only")
    return current_user


# ── Course Management Schemas ──────────────────────────────

class CourseCreateRequest(BaseModel):
    name:                str
    type:                CourseType       # "UG" or "PG"
    seats:               int
    fees:                float
    eligibility_summary: Optional[str] = None   # short display text only
    # NOTE: Full eligibility criteria lives in the uploaded brochure PDF
    #       and is used by the RAG pipeline for screening and student queries.


class CourseUpdateRequest(BaseModel):
    name:                Optional[str]   = None
    seats:               Optional[int]   = None
    fees:                Optional[float] = None
    eligibility_summary: Optional[str]   = None


# ── POST /admin/courses ────────────────────────────────────

@router.post("/courses")
def create_course(
    payload: CourseCreateRequest,
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    """
    Director adds a course via the dashboard form.
    Eligibility criteria for screening comes from the uploaded brochure PDF (RAG),
    not from this form — this is just the structured metadata students see.
    """
    existing = db.query(Course).filter(Course.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Course '{payload.name}' already exists.")

    course = Course(
        name                = payload.name,
        type                = payload.type,
        seats               = payload.seats,
        fees                = payload.fees,
        eligibility_summary = payload.eligibility_summary
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"message": f"Course '{course.name}' created.", "course_id": course.id}


# ── PUT /admin/courses/{id} ────────────────────────────────

@router.put("/courses/{course_id}")
def update_course(
    course_id: int,
    payload: CourseUpdateRequest,
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if payload.name is not None:
        course.name = payload.name
    if payload.seats is not None:
        course.seats = payload.seats
    if payload.fees is not None:
        course.fees = payload.fees
    if payload.eligibility_summary is not None:
        course.eligibility_summary = payload.eligibility_summary

    db.commit()
    return {"message": f"Course '{course.name}' updated."}


# ── DELETE /admin/courses/{id} ─────────────────────────────

@router.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Prevent deletion if students have applied
    applications = db.query(Application).filter(Application.course_id == course_id).count()
    if applications > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {applications} student(s) have applied for this course."
        )

    db.delete(course)
    db.commit()
    return {"message": f"Course '{course.name}' deleted."}


# ── GET /admin/applicants ──────────────────────────────────

@router.get("/applicants")
def get_applicants(
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    applications = db.query(Application).all()

    buckets = {
        "auto_selected": [],
        "auto_rejected": [],
        "borderline":    [],
        "pending":       [],
        "selected":      [],
        "rejected":      []
    }

    for app in applications:
        student = db.query(User).filter(User.id == app.student_id).first()
        course  = db.query(Course).filter(Course.id == app.course_id).first()

        from models.db_models import Document
        doc_type = "marksheet_12th" if course.type == "UG" else "marksheet_btech"
        doc = db.query(Document).filter(
            Document.student_id == app.student_id,
            Document.type == doc_type
        ).first()

        entry = {
            "application_id":  app.id,
            "student_id":      student.id,
            "student_name":    student.name,
            "student_email":   student.email,
            "course":          course.name,
            "course_type":     course.type,
            "status":          app.status,
            "screening_notes": app.screening_notes,
            "applied_on":      app.created_at,
            "marks":           doc.extracted_marks if doc else None,
            "marksheet_url":   doc.file_url if doc else None
        }

        bucket_key = app.status if app.status in buckets else "pending"
        buckets[bucket_key].append(entry)

    return buckets


# ── POST /admin/override ───────────────────────────────────

@router.post("/override")
def override_decision(
    payload: OverrideRequest,
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == payload.application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    old_status = application.status
    application.status = ApplicationStatus(payload.new_status)
    application.screening_notes = (
        f"[Director override] {payload.note}"
        if payload.note
        else f"[Director override: {old_status} → {payload.new_status}]"
    )

    db.commit()
    return {
        "message":    f"Application {payload.application_id} updated.",
        "old_status": old_status,
        "new_status": payload.new_status
    }


# ── POST /admin/screen-all ─────────────────────────────────

@router.post("/screen-all")
def run_screening(
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    result = screen_all_pending(db)
    return {"message": "Screening complete", "result": result}


# ── POST /admin/exam-schedule ──────────────────────────────

@router.post("/exam-schedule", response_model=ExamScheduleResponse)
def set_exam_schedule(
    payload: ExamScheduleRequest,
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    schedule = db.query(ExamSchedule).filter(
        ExamSchedule.course_id == payload.course_id
    ).first()

    if schedule:
        schedule.exam_date           = payload.exam_date
        schedule.venue               = payload.venue
        schedule.result_release_date = payload.result_release_date
    else:
        schedule = ExamSchedule(
            course_id           = payload.course_id,
            exam_date           = payload.exam_date,
            venue               = payload.venue,
            result_release_date = payload.result_release_date
        )
        db.add(schedule)

    db.commit()
    db.refresh(schedule)
    return schedule


# ── POST /admin/finalize ───────────────────────────────────

@router.post("/finalize")
def finalize_decisions(
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    borderline_count = db.query(Application).filter(
        Application.status == ApplicationStatus.borderline
    ).count()

    if borderline_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"{borderline_count} borderline application(s) need manual review first."
        )

    db.query(Application).filter(
        Application.status == ApplicationStatus.auto_selected
    ).update(
        {Application.status: ApplicationStatus.selected,
         Application.finalized_at: datetime.utcnow()},
        synchronize_session=False
    )
    db.query(Application).filter(
        Application.status == ApplicationStatus.auto_rejected
    ).update(
        {Application.status: ApplicationStatus.rejected,
         Application.finalized_at: datetime.utcnow()},
        synchronize_session=False
    )
    db.commit()

    selected = db.query(func.count(Application.id)).filter(
        Application.status == ApplicationStatus.selected).scalar()
    rejected = db.query(func.count(Application.id)).filter(
        Application.status == ApplicationStatus.rejected).scalar()

    return {
        "message":   "Decisions finalized. Ready to send emails.",
        "selected":  selected,
        "rejected":  rejected,
        "next_step": "POST /email/send-results"
    }


# ── GET /admin/stats ───────────────────────────────────────

@router.get("/stats")
def get_stats(
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    total = db.query(func.count(Application.id)).scalar() or 0
    by_status = (
        db.query(Application.status, func.count(Application.id))
        .group_by(Application.status).all()
    )
    by_course = (
        db.query(Course.name, Course.type, func.count(Application.id))
        .join(Application, Application.course_id == Course.id)
        .group_by(Course.name, Course.type).all()
    )
    from sqlalchemy import cast, Date
    daily = (
        db.query(
            cast(Application.created_at, Date).label("date"),
            func.count(Application.id).label("count")
        )
        .group_by(cast(Application.created_at, Date))
        .order_by(cast(Application.created_at, Date).desc())
        .limit(7).all()
    )

    return {
        "total_applications": total,
        "by_status":  {str(s): c for s, c in by_status},
        "by_course":  [{"course": n, "type": t, "count": c} for n, t, c in by_course],
        "daily_trend":[{"date": str(d), "count": c} for d, c in daily]
    }


# ── POST /admin/generate-admit-card/{application_id} ──────

import os as _os
SUPABASE_URL         = _os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = _os.getenv("SUPABASE_SERVICE_KEY")


@router.post("/generate-admit-card/{application_id}")
async def generate_admit_card(
    application_id: int,
    director: User = Depends(get_director),
    db: Session = Depends(get_db)
):
    """
    Director generates and stores an admit card for a selected student.
    - Only allowed when application is auto_selected or selected.
    - Uses the admit_card template uploaded by the director.
    - Stores the generated PDF in Supabase and saves a Document record.
    - Student can then see + download it from their dashboard.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.status not in ("auto_selected", "selected"):
        raise HTTPException(
            status_code=400,
            detail="Admit card can only be issued for auto-selected or selected students."
        )

    course = db.query(Course).filter(Course.id == application.course_id).first()

    try:
        from services.email_service import generate_and_store_admit_card, generate_roll_number
        file_url = await generate_and_store_admit_card(db, application)
        roll_no  = generate_roll_number(application.id, course) 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": f"Admit card generated and stored.",
        "url": file_url,
        "roll_no": roll_no
    }

    return {
        "message":   f"Admit card generated for {student.name}.",
        "roll_no":   roll_no,
        "file_url":  file_url,
    }