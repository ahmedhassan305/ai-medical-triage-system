from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models import PatientProfile, User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.patient import normalize_patient_sex
from app.services.egyptian_national_id import calculate_age, parse_egyptian_national_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    patient_profile: PatientProfile | None = None
    if payload.role == "patient":
        try:
            national_id_info = parse_egyptian_national_id(payload.national_id or "")
            patient_profile = PatientProfile(
                full_name=(payload.full_name or "").strip(),
                age=calculate_age(national_id_info.date_of_birth),
                sex=normalize_patient_sex(payload.sex or ""),
                national_id=national_id_info.national_id,
                date_of_birth=national_id_info.date_of_birth,
                inferred_governorate_code=national_id_info.inferred_governorate_code,
                inferred_governorate=national_id_info.inferred_governorate,
                current_governorate=national_id_info.inferred_governorate,
                smoker=False,
                alcoholic=False,
                chronic_conditions=[],
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        db.flush()
        if patient_profile is not None:
            patient_profile.user_id = user.id
            db.add(patient_profile)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This national ID is already linked to another patient profile.",
        ) from exc

    db.refresh(user)
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user, from_attributes=True)
