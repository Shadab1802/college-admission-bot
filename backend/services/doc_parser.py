"""
doc_parser.py
Handles: PDF/DOCX → text → chunks → embeddings → stored in doc_chunks table
"""
import os
import io
from pathlib import Path
from typing import List

import fitz                          # PyMuPDF for PDF
import numpy as np
from PIL import Image
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from models.db_models import CollegeDoc, DocChunk

# ── EasyOCR Lazy Loader ─────────────────────────────────────
_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        print("[DocParser] Loading EasyOCR models...")
        _ocr_reader = easyocr.Reader(['en'])
    return _ocr_reader

# ── Embedding model (runs locally, no API cost) ────────────
# 384-dim vectors, fast, good quality for RAG
_embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ── Text splitter ──────────────────────────────────────────
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "]
)


# ── Extraction ─────────────────────────────────────────────

def parse_marksheet_text_with_llm(text: str) -> dict:
    """
    Uses Groq to extract structured marks (percentage/CGPA) from raw text.
    """
    import os
    import json
    from groq import Groq
    
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""
    You are an expert academic document analyzer. Your task is to extract the final aggregate percentage or CGPA from a student's marksheet.
    The text below may come from OCR and could be messy, out of order, or contain typos.
    
    Instructions:
    1. Look for an explicit "Aggregate Percentage", "Total Percentage", or "CGPA".
    2. If NOT found, look for "Grand Total", "Total Marks Obtained", and "Maximum Marks" (e.g., 401 out of 500).
    3. If you find a total like "401" and it mentions "5 subjects", calculate the percentage as (401/500)*100 = 80.2.
    4. Board: Look for CBSE, ICSE, or State boards (e.g., WBCHSE).
    
    Return ONLY a JSON object with these keys: "percentage" (number), "cgpa" (number), "board" (string).
    If a value is not found, use null.
    
    Rules:
    - Return a SINGLE percentage value. 
    - If you calculate it, round to 2 decimal places.
    - Ignore individual subject marks.
    
    Marksheet Text (from OCR):
    ---
    {text[:5000]}
    ---
    """
    
    try:
        print(f"[DocParser] Sending {len(text)} chars to LLM for marks extraction...")
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "You are a precise data extraction tool. You can perform basic arithmetic to calculate percentages if they are not explicitly stated."},
                      {"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        data = json.loads(resp.choices[0].message.content)
        print(f"[DocParser] LLM Extracted: {data}")
        return data
    except Exception as e:
        print(f"[DocParser] LLM Extraction failed: {e}")
        return {"percentage": None, "cgpa": None, "board": None}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "\n\n".join(page.get_text() for page in doc)
    print(f"[DocParser] PyMuPDF extracted {len(text)} characters.")
    
    # If text is too sparse, it's likely a scan. Try OCR.
    if len(text.strip()) < 100:
        print("[DocParser] PDF looks like a scan (sparse text). Running EasyOCR fallback...")
        ocr_text = []
        reader = get_ocr_reader()
        
        for i, page in enumerate(doc):
            print(f"[DocParser] OCRing page {i+1}...")
            # Convert page to image (pixmap)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
            img_data = pix.tobytes("png")
            
            results = reader.readtext(img_data, detail=0)
            ocr_text.append(" ".join(results))
            
        final_text = "\n\n".join(ocr_text)
        print(f"[DocParser] OCR complete. Total chars: {len(final_text)}")
        return final_text
        
    return text


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = DocxDocument(io.BytesIO(file_bytes))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ── Chunking + Embedding ───────────────────────────────────

def chunk_and_embed(text: str) -> List[dict]:
    """Returns list of {chunk_text, embedding}"""
    chunks = _splitter.split_text(text)
    embeddings = _embedder.encode(chunks, show_progress_bar=False)
    return [
        {"chunk_text": chunk, "embedding": emb.tolist()}
        for chunk, emb in zip(chunks, embeddings)
    ]


def embed_query(query: str) -> List[float]:
    """Embed a single query string for similarity search"""
    return _embedder.encode(query).tolist()


# ── Main pipeline: parse → chunk → store ──────────────────

def process_and_store_document(
    db: Session,
    college_doc_id: int,
    file_bytes: bytes,
    filename: str
) -> int:
    """
    Full pipeline:
    1. Extract text from file
    2. Chunk it
    3. Embed each chunk
    4. Store in doc_chunks table
    Returns: number of chunks stored
    """
    # Delete old chunks for this doc (handles re-upload / versioning)
    db.query(DocChunk).filter(DocChunk.college_doc_id == college_doc_id).delete()
    db.commit()

    text = extract_text(file_bytes, filename)
    chunks = chunk_and_embed(text)

    for item in chunks:
        chunk = DocChunk(
            college_doc_id=college_doc_id,
            chunk_text=item["chunk_text"],
            embedding=item["embedding"]
        )
        db.add(chunk)

    db.commit()
    return len(chunks)