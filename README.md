# Aria — The Intelligent College Admission Portal 

Aria is a production-grade, AI-powered admission automation pipeline designed to streamline the college application process for both students and administrators. It combines local OCR, Retrieval-Augmented Generation (RAG), and automated document workflows to provide a seamless "bot-first" experience.

##  Key Features

###  1. AI Admission Assistant (Chatbot)
- **RAG-Powered**: Uses local embeddings (`all-MiniLM-L6-v2`) and a vector database (pgvector) to answer student queries based on the official college brochure and rules.
- **Context-Aware**: Understands eligibility, fee structures, and course details without manual intervention.

###  2. Automated Screening & OCR
- **Local OCR Extraction**: Uses **EasyOCR** (powered by PyTorch) to extract marks from scanned 12th/UG marksheets locally on the server (ensuring 100% data privacy).
- **Intelligent Evaluation**: Uses Groq-LLM to compare extracted marks against college eligibility criteria fetched dynamically from the RAG system.
- **Status Classification**: Automatically marks students as `Auto-Selected`, `Auto-Rejected`, or `Borderline` for manual review.

###  3. Automated Results & Document Generation
- **Dynamic Template Filling**: Programmatically populates professional `.docx` templates for selection letters, admit cards, and rejection letters.
- **PDF Conversion**: Preserves high-fidelity formatting, logos, and signatures in generated PDFs.
- **Intelligent Emailing**: A robust email service that handles result notifications. It tracks mailed outcomes and allows for automated "Correction Emails" if a director changes a decision.
- **Scheduled Releases**: An automated scheduler triggers result emails for all students once the `result_release_date` passes.

###  4. Director & Student Dashboards
- **Director Panel**: Real-time stats, applicant filtering, manual decision overrides, template management, and one-click "Send Results" button.
- **Student Dashboard**: Application progress tracking, marksheet upload with instant AI feedback, and admit card download.

##  Technology Stack
- **Backend**: FastAPI (Python), SQLAlchemy (ORM), Alembic (Migrations), APScheduler.
- **Frontend**: React (Vite), Vanilla CSS (Modern UI/UX).
- **AI/ML**: Groq (LLM Inference), PyMuPDF, Pytesseract (OCR), Sentence-Transformers.
- **Database**: PostgreSQL with `pgvector` (via Supabase).
- **Storage**: Supabase Storage for templates and generated documents.

##  Deployment (Docker / EC2)
The project is optimized for deployment using **Docker** or high-resource servers like **AWS EC2**. 

> [!NOTE]
> Since the project uses **EasyOCR** (PyTorch) for high-accuracy local processing, ensure your server has at least 2GB of RAM for smooth performance.

### Environment Variables
Ensure the following are set in your `.env` or Render environment:
- `SUPABASE_URL` & `SUPABASE_SERVICE_KEY`
- `DATABASE_URL` (with pgvector support)
- `GROQ_API_KEY`
- `GMAIL_SENDER` & `GMAIL_APP_PASSWORD`
- `ALLOWED_ORIGINS` (for CORS)

##  Getting Started
1. **Clone the Repo**
2. **Backend**:
   - `pip install -r requirements.txt`
   - `alembic upgrade head`
   - `uvicorn main:app --reload`
3. **Frontend**:
   - `npm install`
   - `npm run dev`

---
*Built with ❤️ for Institute of Engineering and Management, Kolkata.*
