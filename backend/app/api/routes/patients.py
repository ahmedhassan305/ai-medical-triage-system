from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import PatientProfile, User
from app.db.session import get_db
from app.schemas.patient import (
    ManagedPatientProfileCreate,
    PatientProfileResponse,
    PatientProfileUpsert,
)
from app.services.egyptian_national_id import (
    calculate_age,
    parse_egyptian_national_id,
)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=list[PatientProfileResponse])
def list_patients(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> list[PatientProfileResponse]:
    profiles = db.query(PatientProfile).order_by(PatientProfile.full_name.asc()).all()
    return [
        PatientProfileResponse.model_validate(profile, from_attributes=True)
        for profile in profiles
    ]


@router.post("/me", response_model=PatientProfileResponse)
def upsert_my_profile(
    payload: PatientProfileUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "admin")),
) -> PatientProfileResponse:
    profile_data = payload.model_dump()
    national_id = profile_data.get("national_id")
    if national_id:
        try:
            national_id_info = parse_egyptian_national_id(national_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        profile_data["national_id"] = national_id_info.national_id
        profile_data["date_of_birth"] = national_id_info.date_of_birth
        profile_data["inferred_governorate_code"] = (
            national_id_info.inferred_governorate_code
        )
        profile_data["inferred_governorate"] = national_id_info.inferred_governorate
        profile_data["age"] = calculate_age(national_id_info.date_of_birth)
        if not profile_data.get("current_governorate"):
            profile_data["current_governorate"] = national_id_info.inferred_governorate
    else:
        profile_data["date_of_birth"] = None
        profile_data["inferred_governorate_code"] = None
        profile_data["inferred_governorate"] = None

    profile = (
        db.query(PatientProfile)
        .filter(PatientProfile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        profile = PatientProfile(user_id=current_user.id, **profile_data)
        db.add(profile)
    else:
        for key, value in profile_data.items():
            setattr(profile, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This national ID is already linked to another patient profile.",
        ) from exc
    db.refresh(profile)
    return PatientProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/me", response_model=PatientProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "admin")),
) -> PatientProfileResponse:
    profile = (
        db.query(PatientProfile)
        .filter(PatientProfile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return PatientProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/by-national-id/{national_id}", response_model=PatientProfileResponse)
def get_patient_by_national_id(
    national_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> PatientProfileResponse:
    try:
        normalized_national_id = parse_egyptian_national_id(national_id).national_id
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    profile = (
        db.query(PatientProfile)
        .filter(PatientProfile.national_id == normalized_national_id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return PatientProfileResponse.model_validate(profile, from_attributes=True)


@router.post("/", response_model=PatientProfileResponse, status_code=201)
def create_patient_profile(
    payload: ManagedPatientProfileCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> PatientProfileResponse:
    try:
        national_id_info = parse_egyptian_national_id(payload.national_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = (
        db.query(PatientProfile)
        .filter(PatientProfile.national_id == national_id_info.national_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="This national ID is already linked to another patient profile.",
        )

    profile = PatientProfile(
        user_id=None,
        full_name=payload.full_name.strip(),
        age=calculate_age(national_id_info.date_of_birth),
        sex=payload.sex,
        national_id=national_id_info.national_id,
        date_of_birth=national_id_info.date_of_birth,
        inferred_governorate_code=national_id_info.inferred_governorate_code,
        inferred_governorate=national_id_info.inferred_governorate,
        current_governorate=payload.current_governorate
        or national_id_info.inferred_governorate,
        smoker=payload.smoker,
        alcoholic=payload.alcoholic,
        chronic_conditions=payload.chronic_conditions,
    )
    db.add(profile)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This national ID is already linked to another patient profile.",
        ) from exc

    db.refresh(profile)
    return PatientProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/{patient_id}", response_model=PatientProfileResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> PatientProfileResponse:
    profile = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return PatientProfileResponse.model_validate(profile, from_attributes=True)


def _format_patient_search_result(patient_id: int, full_name: str | None) -> str:
    if full_name is None:
        return (
            "----------------------------\n"
            "🔍 Patient Search Result\n"
            "----------------------------\n\n"
            "🆔 Patient ID:\n"
            f"{patient_id}\n\n"
            "❌ Status:\n"
            "No patient found with this ID.\n\n"
            "----------------------------"
        )

    return (
        "----------------------------\n"
        "🔍 Patient Search Result\n"
        "----------------------------\n\n"
        "🆔 Patient ID:\n"
        f"{patient_id}\n\n"
        "👤 Patient Name:\n"
        f"{full_name}\n\n"
        "✅ Status:\n"
        "Patient found successfully.\n\n"
        "----------------------------"
    )


@router.get("/{patient_id}/search-result", response_class=PlainTextResponse)
def get_patient_search_result(
    patient_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> str:
    profile = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    full_name = profile.full_name if profile is not None else None
    return _format_patient_search_result(patient_id, full_name)
