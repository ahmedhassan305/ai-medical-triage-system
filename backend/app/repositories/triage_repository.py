from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLog,
    PatientProfile,
    RetrievedChunkLog,
    TriageResult,
    TriageSession,
    User,
)
from app.rag.retriever import RetrievedChunk
from app.schemas.triage import ReasonerOutput, TriageDecision, TriageHistoryItem


class TriageRepository:
    def create_triage_record(
        self,
        db: Session,
        *,
        user_id: int | None,
        patient_id: int | None,
        query: str,
        history_used: bool,
        decision: TriageDecision,
        reasoner_output: ReasonerOutput,
        response_confidence: float,
        response_red_flags: list[str],
        actions: list[str],
        disclaimer: str,
        sources: list[dict[str, str | float]],
        chunks: list[RetrievedChunk],
    ) -> int:
        session = TriageSession(
            user_id=user_id,
            patient_id=patient_id,
            query=query,
            heuristic_level=decision.heuristic_level,
            embedding_level=decision.embedding_level,
            llm_level=decision.llm_level,
            final_level=decision.final_level,
            history_used=history_used,
        )
        db.add(session)
        db.flush()

        result = TriageResult(
            triage_session_id=session.id,
            summary=reasoner_output.summary,
            risk_reasoning=reasoner_output.risk_reasoning,
            recommended_action=reasoner_output.recommended_action,
            confidence=response_confidence,
            red_flags=response_red_flags,
            actions=actions,
            disclaimer=disclaimer,
            sources=sources,
            decision_payload=decision.model_dump(),
            reasoner_payload=reasoner_output.model_dump(),
        )
        db.add(result)

        for rank, chunk in enumerate(chunks, start=1):
            db.add(
                RetrievedChunkLog(
                    triage_session_id=session.id,
                    doc_id=chunk.doc_id,
                    source_file=chunk.source_file,
                    chunk_id=chunk.chunk_id,
                    source=chunk.source,
                    title=chunk.title,
                    url=chunk.url,
                    score=chunk.score,
                    rank=rank,
                    snippet=chunk.text[:1000],
                )
            )

        db.commit()
        return session.id

    def list_history(
        self,
        db: Session,
        *,
        current_user: User,
        limit: int,
        offset: int,
    ) -> tuple[list[TriageHistoryItem], int]:
        query = db.query(TriageSession)

        if current_user.role == "admin":
            pass
        elif current_user.role == "patient":
            patient_profile = (
                db.query(PatientProfile)
                .filter(PatientProfile.user_id == current_user.id)
                .first()
            )
            if patient_profile is None:
                query = query.filter(TriageSession.user_id == current_user.id)
            else:
                query = query.filter(
                    or_(
                        TriageSession.user_id == current_user.id,
                        TriageSession.patient_id == patient_profile.id,
                    )
                )
        else:
            query = query.filter(TriageSession.user_id == current_user.id)

        total = query.with_entities(func.count(TriageSession.id)).scalar() or 0
        sessions = (
            query.order_by(TriageSession.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            TriageHistoryItem(
                id=item.id,
                query=item.query,
                triage_level=item.final_level,
                confidence=item.result.confidence if item.result else 0.0,
                history_used=item.history_used,
                patient_id=item.patient_id,
                created_at=item.created_at,
            )
            for item in sessions
        ]
        return items, total

    def get_history_detail(
        self,
        db: Session,
        *,
        current_user: User,
        triage_id: int,
    ) -> TriageSession | None:
        query = db.query(TriageSession).filter(TriageSession.id == triage_id)

        if current_user.role == "patient":
            patient_profile = (
                db.query(PatientProfile)
                .filter(PatientProfile.user_id == current_user.id)
                .first()
            )
            if patient_profile is None:
                query = query.filter(TriageSession.user_id == current_user.id)
            else:
                query = query.filter(
                    or_(
                        TriageSession.user_id == current_user.id,
                        TriageSession.patient_id == patient_profile.id,
                    )
                )
        elif current_user.role != "admin":
            query = query.filter(TriageSession.user_id == current_user.id)

        return query.first()

    def log_audit(
        self,
        db: Session,
        *,
        user_id: int | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        status: str,
        ip_address: str | None,
        details: dict[str, object] | None = None,
    ) -> None:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                ip_address=ip_address,
                details=details,
            )
        )
        db.commit()
