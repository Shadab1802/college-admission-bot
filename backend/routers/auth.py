from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.db_models import User, UserRole
from schemas.auth_schemas import RegisterRequest, TokenResponse
from core.security import hash_password, verify_password, create_access_token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # Check duplicate email
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name          = payload.name,
        email         = payload.email,
        password_hash = hash_password(payload.password),
        role          = UserRole.student  # Security: Only allow student registration
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"user_id": user.id, "role": user.role})
    return TokenResponse(
        access_token = token,
        role         = user.role,
        name         = user.name,
        user_id      = user.id
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"user_id": user.id, "role": user.role})
    return TokenResponse(
        access_token = token,
        role         = user.role,
        name         = user.name,
        user_id      = user.id
    )


@router.get("/me")
def get_me(db: Session = Depends(get_db), token: str = ""):
    """Quick sanity check endpoint — returns current user info"""
    from core.security import get_current_user
    # Actual dependency injection used via router in main.py
    pass