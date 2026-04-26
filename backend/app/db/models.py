from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True, default="patient")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient_profile: Mapped["PatientProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
    doctor_profile: Mapped["DoctorProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
    triage_sessions: Mapped[list["TriageSession"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(String(200))
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(20))
    smoker: Mapped[bool] = mapped_column(Boolean, default=False)
    alcoholic: Mapped[bool] = mapped_column(Boolean, default=False)
    chronic_conditions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user: Mapped[User | None] = relationship(back_populates="patient_profile")
    visits: Mapped[list["Visit"]] = relationship(back_populates="patient")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")
    triage_sessions: Mapped[list["TriageSession"]] = relationship(
        back_populates="patient"
    )


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(String(200))
    specialty: Mapped[str] = mapped_column(String(120))
    clinic: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user: Mapped[User | None] = relationship(back_populates="doctor_profile")
    visits: Mapped[list["Visit"]] = relationship(back_populates="doctor")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    doctor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("doctor_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    symptoms: Mapped[str] = mapped_column(Text)
    vitals: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    prescriptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped[PatientProfile] = relationship(back_populates="visits")
    doctor: Mapped[DoctorProfile | None] = relationship(back_populates="visits")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30), default="requested", index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped[PatientProfile] = relationship(back_populates="appointments")
    doctor: Mapped[DoctorProfile] = relationship(back_populates="appointments")


class TriageSession(Base):
    __tablename__ = "triage_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    patient_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("patient_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text)
    heuristic_level: Mapped[str] = mapped_column(String(20), index=True)
    embedding_level: Mapped[str] = mapped_column(String(20), index=True)
    llm_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    final_level: Mapped[str] = mapped_column(String(20), index=True)
    history_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User | None] = relationship(back_populates="triage_sessions")
    patient: Mapped[PatientProfile | None] = relationship(
        back_populates="triage_sessions"
    )
    result: Mapped["TriageResult | None"] = relationship(
        back_populates="session",
        uselist=False,
    )
    retrieved_chunks: Mapped[list["RetrievedChunkLog"]] = relationship(
        back_populates="session"
    )


class TriageResult(Base):
    __tablename__ = "triage_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    triage_session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("triage_sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text)
    risk_reasoning: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column()
    red_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    disclaimer: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict[str, str | float]]] = mapped_column(JSON, default=list)
    decision_payload: Mapped[dict[str, str | float | None]] = mapped_column(JSON)
    reasoner_payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[TriageSession] = relationship(back_populates="result")


class RetrievedChunkLog(Base):
    __tablename__ = "retrieved_chunks_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    triage_session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("triage_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    doc_id: Mapped[str] = mapped_column(String(255), index=True)
    source_file: Mapped[str] = mapped_column(String(255))
    chunk_id: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column()
    rank: Mapped[int] = mapped_column(Integer)
    snippet: Mapped[str] = mapped_column(Text)

    session: Mapped[TriageSession] = relationship(back_populates="retrieved_chunks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(120), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User | None] = relationship(back_populates="audit_logs")
