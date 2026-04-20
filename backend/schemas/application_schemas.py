from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class ApplicationStatusEnum(str, Enum):
    pending           = "pending"
    auto_selected     = "auto_selected"
    auto_rejected     = "auto_rejected"
    borderline        = "borderline"
    selected          = "selected"
    rejected          = "rejected"


# ── Application ────────────────────────────────────────────

class ApplyRequest(BaseModel):
    course_id: int


class ApplicationResponse(BaseModel):
    id:              int
    course_id:       int
    course_name:     str
    course_type:     str
    status:          str
    screening_notes: Optional[str]
    created_at:      datetime

    class Config:
        from_attributes = True


# ── Course ─────────────────────────────────────────────────

class CourseResponse(BaseModel):
    id:                  int
    name:                str
    type:                str
    seats:               int
    fees:                float
    eligibility_summary: Optional[str]

    class Config:
        from_attributes = True


# ── Director override ──────────────────────────────────────

class OverrideRequest(BaseModel):
    application_id: int
    new_status:     ApplicationStatusEnum
    note:           Optional[str] = None


# ── Exam Schedule ──────────────────────────────────────────

class ExamScheduleRequest(BaseModel):
    course_id:           int
    exam_date:           datetime
    venue:               str
    result_release_date: datetime


class ExamScheduleResponse(BaseModel):
    course_id:           int
    exam_date:           Optional[datetime]
    venue:               Optional[str]
    syllabus_url:        Optional[str]
    result_release_date: Optional[datetime]

    class Config:
        from_attributes = True