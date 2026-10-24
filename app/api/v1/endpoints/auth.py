from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate
from app.schemas.auth import UserLogin, TokenResponse
from app.core.security import (
    hash_password, verify_password, create_access_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(409, "Email already registered")

    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "created_at": user.created_at}


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form_data.username.lower()
    user = db.scalar(select(User).where(User.email == email))

    if user is None or not verify_password(
        form_data.password, user.password_hash
    ):
        raise HTTPException(401, "Incorrect email or password")

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }
