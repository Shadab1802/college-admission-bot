"""
email.py router

POST /email/send-results            → director triggers result emails to all finalized
POST /email/retry-failed            → retry all failed email sends
POST /email/upload-template         → director uploads Word template
GET  /email/templates               → list uploaded templates
GET  /email/logs                    → view sent/failed email log
"""
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db.database import get_db
from models.db_models import (
    User, Application, Course, ExamSchedule,
    Template, EmailLog, ApplicationStatus, TemplateType
)
from schemas.auth_schemas import TokenData
from core.security import get_current_user, require_director
from services.email_service import send_selected_email, send_rejected_email

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

router = APIRouter(prefix="/email", tags=["Email"])




# ── POST /email/send-results ───────────────────────────────

@router.post("/send-results")
async def send_results(
    director: User = Depends(require_director),
    db: Session = Depends(get_db)
):
    """
    Sends result emails to ALL finalized (selected + rejected) students
    who haven't received an email yet.
    """
    # Only finalized applications
    finalized = db.query(Application).filter(
        Application.status.in_([ApplicationStatus.selected, ApplicationStatus.rejected]),
        Application.finalized_at.isnot(None)
    ).all()

    if not finalized:
        return {"message": "No finalized applications found. Run /admin/finalize first."}

    # Map student_id -> last_sent_status (avoid duplicates unless status changed)
    sent_logs = db.query(EmailLog).filter(
        EmailLog.type == "result",
        EmailLog.status == "sent"
    ).all()
    last_sent_map = {log.student_id: log.result_status for log in sent_logs}

    results = {"sent_selected": 0, "sent_rejected": 0, "failed": 0, "skipped": 0}

    for app in finalized:
        if last_sent_map.get(app.student_id) == app.status:
            results["skipped"] += 1
            continue

        student  = db.query(User).filter(User.id == app.student_id).first()
        course   = db.query(Course).filter(Course.id == app.course_id).first()
        schedule = db.query(ExamSchedule).filter(
            ExamSchedule.course_id == app.course_id
        ).first()

        if app.status == ApplicationStatus.selected:
            success = await send_selected_email(db, app, student, course, schedule)
            if success:
                results["sent_selected"] += 1
            else:
                results["failed"] += 1

        elif app.status == ApplicationStatus.rejected:
            success = await send_rejected_email(db, app, student, course)
            if success:
                results["sent_rejected"] += 1
            else:
                results["failed"] += 1

    return {
        "message": "Result emails dispatched.",
        "results": results
    }


# ── POST /email/retry-failed ───────────────────────────────

@router.post("/retry-failed")
async def retry_failed(
    director: User = Depends(require_director),
    db: Session = Depends(get_db)
):
    """Retry sending to students whose emails previously failed"""
    failed_logs = db.query(EmailLog).filter(EmailLog.status == "failed").all()

    if not failed_logs:
        return {"message": "No failed emails to retry."}

    retried = 0
    success_count = 0

    for log in failed_logs:
        app = db.query(Application).filter(
            Application.student_id == log.student_id
        ).first()
        if not app:
            continue

        student  = db.query(User).filter(User.id == log.student_id).first()
        course   = db.query(Course).filter(Course.id == app.course_id).first()
        schedule = db.query(ExamSchedule).filter(
            ExamSchedule.course_id == app.course_id
        ).first()

        if app.status == ApplicationStatus.selected:
            success = await send_selected_email(db, app, student, course, schedule)
        else:
            success = await send_rejected_email(db, app, student, course)

        retried += 1
        if success:
            success_count += 1
            # Mark old log as resolved
            log.status = "sent"
            db.commit()

    return {
        "message":   f"Retried {retried} emails.",
        "succeeded": success_count,
        "still_failed": retried - success_count
    }


# ── POST /email/upload-template ────────────────────────────

@router.post("/upload-template")
async def upload_template(
    template_type: TemplateType,
    file: UploadFile = File(...),
    director: User = Depends(require_director),
    db: Session = Depends(get_db)
):
    """
    Director uploads a Word (.docx) template for:
      - result_selected  → selection letter sent to accepted students
      - result_rejected  → rejection letter
      - admit_card       → admit card with roll number, exam details

    Use these placeholders in your Word doc:
      {{student_name}}, {{course_name}}, {{roll_number}},
      {{exam_date}}, {{venue}}, {{fees}}, {{date}},
      {{college_name}}, {{college_address}}
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in (".docx", ".doc"):
        raise HTTPException(status_code=400, detail="Only .docx templates accepted")

    file_bytes = await file.read()

    # ── Upload to Supabase Storage ─────────────────────────
    storage_name = f"templates/{template_type.value}.docx"
    upload_url   = f"{SUPABASE_URL}/storage/v1/object/templates/{template_type.value}.docx"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            upload_url,
            content=file_bytes,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "x-upsert": "true"
            }
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Upload failed: {resp.text}")

    file_url = f"{SUPABASE_URL}/storage/v1/object/public/templates/{template_type.value}.docx"

    # ── Save or update template record ────────────────────
    existing = db.query(Template).filter(Template.type == template_type).first()
    if existing:
        existing.file_url    = file_url
        existing.uploaded_by = director.id
        db.commit()
    else:
        tmpl = Template(
            type        = template_type,
            file_url    = file_url,
            uploaded_by = director.id
        )
        db.add(tmpl)
        db.commit()

    return {
        "message":       f"Template '{template_type.value}' uploaded successfully.",
        "file_url":      file_url,
        "placeholders":  [
            "{{student_name}}", "{{course_name}}", "{{course_type}}",
            "{{roll_number}}", "{{exam_date}}", "{{venue}}",
            "{{fees}}", "{{date}}", "{{application_id}}",
            "{{college_name}}", "{{college_address}}", "{{college_phone}}"
        ]
    }


# ── GET /email/templates ───────────────────────────────────

@router.get("/templates")
def list_templates(
    director: User = Depends(require_director),
    db: Session = Depends(get_db)
):
    templates = db.query(Template).all()
    return [
        {
            "type":       t.type,
            "file_url":   t.file_url,
            "updated_at": t.updated_at
        }
        for t in templates
    ]


# ── GET /email/logs ────────────────────────────────────────

@router.get("/logs")
def email_logs(
    director: User = Depends(require_director),
    db: Session = Depends(get_db)
):
    logs = db.query(EmailLog).order_by(EmailLog.sent_at.desc()).limit(100).all()
    return [
        {
            "student_id": log.student_id,
            "type":       log.type,
            "status":     log.status,
            "sent_at":    log.sent_at,
            "error":      log.error_msg
        }
        for log in logs
    ]