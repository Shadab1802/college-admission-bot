"""
chat.py router
POST /chat/message        → student or director sends a message, gets SSE stream back
POST /chat/upload-doc     → director uploads PDF/DOCX, triggers RAG pipeline
GET  /chat/history        → (optional) retrieve recent chat (stateless for now, frontend manages)
"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
import json

from db.database import get_db
from models.db_models import User, CollegeDoc
from core.security import get_current_user
from schemas.auth_schemas import TokenData
from services.rag_service import stream_chat_response
from services.doc_parser import process_and_store_document

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Schemas ────────────────────────────────────────────────

class ChatMessage(BaseModel):
    content: str
    history: list[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]


# ── POST /chat/message ─────────────────────────────────────

@router.post("/message")
async def chat_message(
    payload: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint. Returns a Server-Sent Events stream.
    Frontend reads this as a ReadableStream for typewriter effect.
    """
    async def event_generator():
        async for token in stream_chat_response(
            db=db,
            user=current_user,
            user_message=payload.content,
            chat_history=payload.history
        ):
            # JSON encode the token to safely preserve newlines and special characters in SSE
            yield f"data: {json.dumps(token)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # important for nginx on Render/Railway
        }
    )


# ── POST /chat/upload-doc (director only) ─────────────────

@router.post("/upload-doc")
async def upload_college_doc(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Director uploads a PDF or DOCX.
    1. File saved to Supabase Storage
    2. Text extracted → chunked → embedded → stored in pgvector
    """
    if current_user.role != "director":
        raise HTTPException(status_code=403, detail="Director access only")

    allowed = {".pdf", ".docx", ".doc"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Only PDF/DOCX allowed. Got: {ext}")

    file_bytes = await file.read()

    # ── Upload to Supabase Storage ─────────────────────────
    storage_path = f"college-docs/{file.filename}"
    upload_url   = f"{SUPABASE_URL}/storage/v1/object/college-docs/{file.filename}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            upload_url,
            content=file_bytes,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": file.content_type or "application/octet-stream",
                "x-upsert": "true"   # overwrite if same filename
            }
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Supabase upload failed: {resp.text}")

    file_url = f"{SUPABASE_URL}/storage/v1/object/public/college-docs/{file.filename}"

    # ── Save metadata to DB ────────────────────────────────
    existing = db.query(CollegeDoc).filter(CollegeDoc.filename == file.filename).first()
    if existing:
        existing.file_url = file_url
        existing.version += 1
        db.commit()
        college_doc_id = existing.id
    else:
        college_doc = CollegeDoc(
            filename    = file.filename,
            file_url    = file_url,
            uploaded_by = current_user.id
        )
        db.add(college_doc)
        db.commit()
        db.refresh(college_doc)
        college_doc_id = college_doc.id

    # ── Process: extract → chunk → embed → store ──────────
    num_chunks = process_and_store_document(
        db            = db,
        college_doc_id= college_doc_id,
        file_bytes    = file_bytes,
        filename      = file.filename
    )

    return {
        "message": f"Document '{file.filename}' processed successfully.",
        "chunks_stored": num_chunks,
        "file_url": file_url
    }


# ── GET /chat/docs (list uploaded college docs) ────────────

@router.get("/docs")
def list_college_docs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    docs = db.query(CollegeDoc).order_by(CollegeDoc.created_at.desc()).all()
    return [
        {
            "id":       d.id,
            "filename": d.filename,
            "version":  d.version,
            "file_url": d.file_url,
            "uploaded_at": d.created_at
        }
        for d in docs
    ]