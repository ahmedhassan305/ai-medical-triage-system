from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models import User
from app.db.session import get_db
from app.repositories.triage_repository import TriageRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
auth_limiter = rate_limit(
    "auth",
    settings.auth_rate_limit_count,
    settings.auth_rate_limit_window_seconds,
)


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(auth_limiter),
) -> UserResponse:
    repository = TriageRepository()
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        repository.log_audit(
            db,
            user_id=None,
            action="auth.register",
            resource_type="user",
            resource_id=payload.email,
            status="conflict",
            ip_address=request.client.host if request.client else None,
            details={"role": payload.role},
        )
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    repository.log_audit(
        db,
        user_id=user.id,
        action="auth.register",
        resource_type="user",
        resource_id=str(user.id),
        status="success",
        ip_address=request.client.host if request.client else None,
        details={"role": user.role},
    )
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(auth_limiter),
) -> TokenResponse:
    repository = TriageRepository()
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        repository.log_audit(
            db,
            user_id=user.id if user else None,
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id) if user else payload.email,
            status="failed",
            ip_address=request.client.host if request.client else None,
            details=None,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(subject=str(user.id), role=user.role)
    repository.log_audit(
        db,
        user_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
        status="success",
        ip_address=request.client.host if request.client else None,
        details={"role": user.role},
    )
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user, from_attributes=True)
