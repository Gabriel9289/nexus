from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import  Optional

from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

from database import get_db
from models import User, Follow

load_dotenv()

SECRET_KEY                 = os.getenv("SECRET_KEY")
ALGORITHM                  = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

router       = APIRouter(prefix="/auth", tags=["Auth"])
pwd_context  = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

class RegisterData(BaseModel):
    username: str
    email: str
    password: str
    display_name: Optional[str] = None

class LoginData(BaseModel):
    email: str
    password: str

# --- Helpers ----====---------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db:    Session = Depends(get_db)
) -> User:
    err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise err
    except JWTError:
        raise err

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise err
    return user


# --- Helpers for counts ----====----

def get_counts(user_id: int, db: Session) -> dict:
    following = db.query(Follow).filter(Follow.follower_id  == user_id).count()
    followers = db.query(Follow).filter(Follow.following_id == user_id).count()
    return {"following_count": following, "follower_count": followers}


# --- Routes ----====----------------

@router.post("/register", status_code=201)
def register(data: RegisterData, db: Session = Depends(get_db)):
    username     = data.username.strip()
    email        = data.email.strip()
    password     = data.password
    display_name = data.display_name or username

    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="username, email and password are required")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id":           user.id,
        "username":     user.username,
        "email":        user.email,
        "display_name": user.display_name,
        "avatar_url":   user.avatar_url,
        "bio":          user.bio,
        "following_count": 0,
        "follower_count":  0,
    }


@router.post("/login")
def login(data:  LoginData, db: Session = Depends(get_db)):
    email    = data.email.strip()
    password = data.password

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token  = create_access_token({"sub": str(user.id)})
    counts = get_counts(user.id, db)

    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "id":           user.id,
            "username":     user.username,
            "email":        user.email,
            "display_name": user.display_name,
            "avatar_url":   user.avatar_url,
            "bio":          user.bio,
            **counts,
        }
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    counts = get_counts(current_user.id, db)
    return {
        "id":           current_user.id,
        "username":     current_user.username,
        "email":        current_user.email,
        "display_name": current_user.display_name,
        "avatar_url":   current_user.avatar_url,
        "bio":          current_user.bio,
        **counts,
    }
