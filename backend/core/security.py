from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from db.database import get_db
from models.db_models import User
from schemas.auth_schemas import TokenData
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

from fastapi.security import OAuth2PasswordBearer
import bcrypt

oauth2_scheme  = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Password utils ─────────────────────────────────────────

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    password_byte_enc = plain.encode('utf-8')
    hashed_byte_enc = hashed.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc, hashed_byte_enc)


# ── Token utils ────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        role:    str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return TokenData(user_id=user_id, role=role)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Current user dependency ────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db)
) -> User:
    token_data = decode_token(token)
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_director(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "director":
        raise HTTPException(status_code=403, detail="Director access only")
    return current_user


def require_student(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")
    return current_user