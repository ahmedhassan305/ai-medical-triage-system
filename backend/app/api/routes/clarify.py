from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.triage import ClarificationRequest, ClarificationResponse
from app.services.clarification_service import build_enriched_query
from app.services.triage_service import triage

router = APIRouter(prefix="/clarify", tags=["clarify"])


@router.post("", response_model=ClarificationResponse)
def clarify_and_triage(
    payload: ClarificationRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ClarificationResponse:
    if payload.patient_id is not None and current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    enriched_query = build_enriched_query(payload.original_query, payload.answers)
    result = triage(
        enriched_query,
        patient_id=payload.patient_id,
        db=db,
    )
    result.needs_clarification = False
    result.questions = []
    return ClarificationResponse(
        needs_clarification=False,
        original_query=payload.original_query,
        confidence_score=result.confidence_score,
        questions=[],
        triage_result=result,
    )
