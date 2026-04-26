from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_user
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.db.models import User
from app.db.session import get_db
from app.schemas.triage import (
    TriageDetail,
    TriageHistoryPage,
    TriageRequest,
    TriageResponse,
)
from app.services.access_control import ensure_patient_access
from app.services.triage_service import (
    get_triage_detail,
    get_triage_history,
)
from app.services.triage_service import (
    triage as run_triage,
)

router = APIRouter(tags=["triage"])
settings = get_settings()
triage_limiter = rate_limit(
    "triage",
    settings.triage_rate_limit_count,
    settings.triage_rate_limit_window_seconds,
)


@router.post("/triage", response_model=TriageResponse)
def triage_route(
    payload: TriageRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    _: None = Depends(triage_limiter),
) -> TriageResponse:
    if payload.patient_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required when patient history is requested.",
            )
        ensure_patient_access(db, current_user, payload.patient_id)

    client_host = request.client.host if request.client else None
    return run_triage(
        payload.query,
        patient_id=payload.patient_id,
        db=db,
        current_user=current_user,
        client_host=client_host,
    )


@router.get("/triage/history", response_model=TriageHistoryPage)
def triage_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TriageHistoryPage:
    return get_triage_history(
        db,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get("/triage/{triage_id}", response_model=TriageDetail)
def triage_detail(
    triage_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TriageDetail:
    detail = get_triage_detail(
        db,
        current_user=current_user,
        triage_id=triage_id,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Triage session not found.")
    return detail
