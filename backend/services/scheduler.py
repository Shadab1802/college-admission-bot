"""
scheduler.py

APScheduler job that runs every hour and checks:
- If any course's result_release_date has passed
- If so, auto-triggers result emails for that course
- Prevents duplicate sends using email_logs table

Start this alongside FastAPI in main.py
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from db.database import SessionLocal
from models.db_models import (
    ExamSchedule, Application, ApplicationStatus,
    User, Course, EmailLog
)
from services.email_service import send_selected_email, send_rejected_email

scheduler = AsyncIOScheduler()


async def check_and_send_scheduled_emails():
    """
    Runs hourly. For each course whose result_release_date has passed,
    sends result emails to all finalized students who haven't been emailed yet.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find schedules whose result date has passed
        due_schedules = db.query(ExamSchedule).filter(
            ExamSchedule.result_release_date <= now,
            ExamSchedule.result_release_date.isnot(None)
        ).all()

        for schedule in due_schedules:
            course_id = schedule.course_id
            course    = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                continue

            # 1. Auto-finalize applications that the director hasn't touched
            # (Move auto_selected -> selected, everything else -> rejected)
            pending_apps = db.query(Application).filter(
                Application.course_id == course_id,
                Application.status.in_([
                    ApplicationStatus.pending,
                    ApplicationStatus.auto_selected,
                    ApplicationStatus.auto_rejected,
                    ApplicationStatus.borderline
                ])
            ).all()

            for app in pending_apps:
                if app.status == ApplicationStatus.auto_selected:
                    app.status = ApplicationStatus.selected
                    app.screening_notes += f"\n[Auto-Finalized on {now.date()}]"
                else:
                    app.status = ApplicationStatus.rejected
                    app.screening_notes += f"\n[Auto-Rejected on {now.date()}]"
                
                app.finalized_at = now
            
            db.commit()

            # 2. Process all applications that are now in a final state (Selected / Rejected)
            finalized_apps = db.query(Application).filter(
                Application.course_id == course_id,
                Application.status.in_([
                    ApplicationStatus.selected,
                    ApplicationStatus.rejected
                ])
            ).all()

            for app in finalized_apps:
                # Skip if already emailed successfully
                already_sent = db.query(EmailLog).filter(
                    EmailLog.student_id == app.student_id,
                    EmailLog.type       == "result",
                    EmailLog.status     == "sent",
                    EmailLog.result_status == app.status
                ).first()
                if already_sent:
                    continue

                student = db.query(User).filter(User.id == app.student_id).first()
                if not student:
                    continue

                print(f"[Scheduler] Processing result for {student.email} ({app.status})")

                try:
                    # For selected students, ensure admit card is in dashboard first
                    if app.status == ApplicationStatus.selected:
                        from services.email_service import generate_and_store_admit_card
                        await generate_and_store_admit_card(db, app)
                        await send_selected_email(db, app, student, course, schedule)
                    elif app.status == ApplicationStatus.rejected:
                        await send_rejected_email(db, app, student, course)
                except Exception as e:
                    print(f"[Scheduler] Error processing {student.email}: {e}")

    except Exception as e:
        print(f"[Scheduler] Error during scheduled email check: {e}")
    finally:
        db.close()


def start_scheduler():
    """Call this from main.py on startup"""
    scheduler.add_job(
        check_and_send_scheduled_emails,
        trigger=IntervalTrigger(hours=1),
        id="result_email_scheduler",
        replace_existing=True,
        next_run_time=datetime.now()   # run immediately on startup too
    )
    scheduler.start()
    print("[Scheduler] Started — checking result dates every hour.")


def stop_scheduler():
    """Call this on app shutdown"""
    scheduler.shutdown()
    print("[Scheduler] Stopped.")