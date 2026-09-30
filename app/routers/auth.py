"""FR-1: register, login, logout."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth import bearer_scheme, get_current_user
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, MessageOut, RegisterRequest, TokenOut, UserOut
from app.utils.security import (
    REVOKED_TOKEN_IDS, create_access_token, decode_token, hash_password, verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Create a new account")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Validates name, email, password (min 8 chars) and confirmation; rejects duplicate emails."""
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut, summary="Log in and receive a JWT")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/logout", response_model=MessageOut, summary="Log out (invalidates the current token)")
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), user: User = Depends(get_current_user)):
    payload = decode_token(credentials.credentials)
    if payload and payload.get("jti"):
        REVOKED_TOKEN_IDS.add(payload["jti"])
    return MessageOut(message="Logged out successfully.")


@router.get("/me", response_model=UserOut, summary="Current user profile")
def me(user: User = Depends(get_current_user)):
    return user
