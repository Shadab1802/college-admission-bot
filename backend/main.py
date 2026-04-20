import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import engine, Base
from routers import auth, chat, applications, admin, email
from services.scheduler import start_scheduler, stop_scheduler


# ── Startup / Shutdown ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="College Admission Bot API",
    version="4.0.0",
    description="Backend for Aria — the college admissions assistant",
    lifespan=lifespan
)

# ── CORS ───────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(applications.router)
app.include_router(admin.router)
app.include_router(email.router)


@app.get("/")
def root():
    return {"message": "Aria API is running 🎓"}

@app.get("/health")
def health():
    """Render uses this to verify the service is up"""
    return {"status": "ok"}