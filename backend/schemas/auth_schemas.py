from pydantic import BaseModel, EmailStr
from enum import Enum


class UserRole(str, Enum):
    student  = "student"
    director = "director"


# ── Register ───────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name:     str
    email:    EmailStr
    password: str
    role:     UserRole = UserRole.student


# ── Login ──────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


# ── Token response ─────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    name:         str
    user_id:      int


# ── User info (used inside JWT payload) ───────────────────
class TokenData(BaseModel):
    user_id: int | None = None
    role:    str | None = None