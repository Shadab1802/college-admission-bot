from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    ForeignKey, Enum, JSON, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from db.database import Base
import enum


# ── Enums ──────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    student = "student"
    director = "director"


class CourseType(str, enum.Enum):
    UG = "UG"
    PG = "PG"


class ApplicationStatus(str, enum.Enum):
    pending             = "pending"
    auto_selected       = "auto_selected"
    auto_rejected       = "auto_rejected"
    borderline          = "borderline"
    selected            = "selected"       # director confirmed
    rejected            = "rejected"       # director confirmed


class DocumentType(str, enum.Enum):
    marksheet_12th  = "marksheet_12th"
    marksheet_btech = "marksheet_btech"
    admit_card      = "admit_card"


class TemplateType(str, enum.Enum):
    admit_card       = "admit_card"
    result_selected  = "result_selected"
    result_rejected  = "result_rejected"


class EmailType(str, enum.Enum):
    result     = "result"
    admit_card = "admit_card"


class EmailStatus(str, enum.Enum):
    sent   = "sent"
    failed = "failed"


# ── Models ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole), nullable=False, default=UserRole.student)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    applications  = relationship("Application", back_populates="student")
    documents     = relationship("Document", back_populates="student")
    email_logs    = relationship("EmailLog", back_populates="student")


class Course(Base):
    __tablename__ = "courses"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String(150), nullable=False)
    type                = Column(Enum(CourseType), nullable=False)
    seats               = Column(Integer, nullable=False)
    fees                = Column(Float, nullable=False)
    eligibility_summary = Column(Text)       # plain text summary for quick display

    applications        = relationship("Application", back_populates="course")
    exam_schedule       = relationship("ExamSchedule", back_populates="course", uselist=False)


class Application(Base):
    __tablename__ = "applications"

    id               = Column(Integer, primary_key=True, index=True)
    student_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id        = Column(Integer, ForeignKey("courses.id"), nullable=False)
    status           = Column(Enum(ApplicationStatus), default=ApplicationStatus.pending)
    screening_notes  = Column(Text)          # bot's reasoning stored here
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    finalized_at     = Column(DateTime(timezone=True), nullable=True)

    student          = relationship("User", back_populates="applications")
    course           = relationship("Course", back_populates="applications")


class Document(Base):
    __tablename__ = "documents"

    id              = Column(Integer, primary_key=True, index=True)
    student_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    type            = Column(Enum(DocumentType), nullable=False)
    file_url        = Column(String(500), nullable=False)   # Supabase storage URL
    extracted_marks = Column(JSON, nullable=True)           # e.g. {"percentage": 82.5, "board": "CBSE"}
    uploaded_at     = Column(DateTime(timezone=True), server_default=func.now())

    student         = relationship("User", back_populates="documents")


class CollegeDoc(Base):
    """Documents uploaded by the director (prospectus, policies, fee structure etc.)"""
    __tablename__ = "college_docs"

    id          = Column(Integer, primary_key=True, index=True)
    filename    = Column(String(200), nullable=False)
    file_url    = Column(String(500), nullable=False)
    version     = Column(Integer, default=1)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    chunks      = relationship("DocChunk", back_populates="college_doc", cascade="all, delete")


class DocChunk(Base):
    """RAG chunks with pgvector embeddings"""
    __tablename__ = "doc_chunks"

    id             = Column(Integer, primary_key=True, index=True)
    college_doc_id = Column(Integer, ForeignKey("college_docs.id"), nullable=False)
    chunk_text     = Column(Text, nullable=False)
    embedding      = Column(Vector(384))        # all-MiniLM-L6-v2 produces 384-dim vectors

    college_doc    = relationship("CollegeDoc", back_populates="chunks")


class Template(Base):
    """Email/admit card templates uploaded by director with {{placeholders}}"""
    __tablename__ = "templates"

    id          = Column(Integer, primary_key=True, index=True)
    type        = Column(Enum(TemplateType), nullable=False, unique=True)
    file_url    = Column(String(500), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class ExamSchedule(Base):
    __tablename__ = "exam_schedule"

    id                  = Column(Integer, primary_key=True, index=True)
    course_id           = Column(Integer, ForeignKey("courses.id"), unique=True, nullable=False)
    exam_date           = Column(DateTime(timezone=True), nullable=True)
    venue               = Column(String(300), nullable=True)
    syllabus_url        = Column(String(500), nullable=True)   # Supabase storage URL
    result_release_date = Column(DateTime(timezone=True), nullable=True)

    course              = relationship("Course", back_populates="exam_schedule")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type       = Column(Enum(EmailType), nullable=False)
    result_status = Column(String(50), nullable=True) # e.g. "selected", "rejected"
    sent_at    = Column(DateTime(timezone=True), server_default=func.now())
    status     = Column(Enum(EmailStatus), nullable=False)
    error_msg  = Column(Text, nullable=True)    # store error if failed

    student    = relationship("User", back_populates="email_logs")