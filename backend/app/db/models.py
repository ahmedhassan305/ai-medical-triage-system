from __future__ import annotations

from datetime import UTC, date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True, default="patient")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient_profile: Mapped["PatientProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
    )
    doctor_profile: Mapped["DoctorProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    doctors: Mapped[list["DoctorProfile"]] = relationship(back_populates="department")


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
    national_id: Mapped[str | None] = mapped_column(
        String(14),
        nullable=True,
        unique=True,
        index=True,
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    inferred_governorate_code: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )
    inferred_governorate: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    current_governorate: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    smoker: Mapped[bool] = mapped_column(Boolean, default=False)
    alcoholic: Mapped[bool] = mapped_column(Boolean, default=False)
    chronic_conditions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    user: Mapped[User | None] = relationship(back_populates="patient_profile")
    visits: Mapped[list["Visit"]] = relationship(back_populates="patient")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")
    triage_assessments: Mapped[list["TriageAssessment"]] = relationship(
        back_populates="patient"
    )
    medical_history: Mapped[list["MedicalHistory"]] = relationship(
        back_populates="patient"
    )
    structured_history: Mapped[list["PatientMedicalHistoryEntry"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    lab_results: Mapped[list["PatientLabResult"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    symptom_links: Mapped[list["PatientSymptom"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
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
    department_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(200))
    specialty: Mapped[str] = mapped_column(String(120))
    clinic: Mapped[str] = mapped_column(String(200))
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    booking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    user: Mapped[User | None] = relationship(back_populates="doctor_profile")
    department: Mapped[Department | None] = relationship(back_populates="doctors")
    visits: Mapped[list["Visit"]] = relationship(back_populates="doctor")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")
    doctor_clinics: Mapped[list["DoctorClinic"]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan",
    )
    schedules: Mapped[list["DoctorSchedule"]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan",
    )
    medical_history_entries: Mapped[list["MedicalHistory"]] = relationship(
        back_populates="doctor"
    )


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    doctor_links: Mapped[list["DoctorClinic"]] = relationship(
        back_populates="clinic",
        cascade="all, delete-orphan",
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="clinic")


class DoctorClinic(Base):
    __tablename__ = "doctor_clinics"
    __table_args__ = (
        UniqueConstraint("doctor_id", "clinic_id", name="uq_doctor_clinic_link"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    clinic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clinics.id", ondelete="CASCADE"),
        index=True,
    )
    scope_at_clinic: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    doctor: Mapped[DoctorProfile] = relationship(back_populates="doctor_clinics")
    clinic: Mapped[Clinic] = relationship(back_populates="doctor_links")
    schedules: Mapped[list["DoctorSchedule"]] = relationship(
        back_populates="doctor_clinic"
    )
    slots: Mapped[list["AppointmentSlot"]] = relationship(
        back_populates="doctor_clinic"
    )


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
    clinic_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("clinics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slot_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("appointment_slots.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30), default="requested", index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped[PatientProfile] = relationship(back_populates="appointments")
    doctor: Mapped[DoctorProfile] = relationship(back_populates="appointments")
    clinic: Mapped[Clinic | None] = relationship(back_populates="appointments")
    slot: Mapped["AppointmentSlot | None"] = relationship(back_populates="appointment")
    triage_assessment: Mapped["TriageAssessment | None"] = relationship(
        back_populates="appointment",
        uselist=False,
    )
    visits: Mapped[list["Visit"]] = relationship(back_populates="appointment")
    medical_history_entries: Mapped[list["MedicalHistory"]] = relationship(
        back_populates="appointment"
    )


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
    appointment_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    symptoms: Mapped[str] = mapped_column(Text)
    vitals: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    prescriptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[PatientProfile] = relationship(back_populates="visits")
    doctor: Mapped[DoctorProfile | None] = relationship(back_populates="visits")
    appointment: Mapped[Appointment | None] = relationship(back_populates="visits")
    medical_history_entry: Mapped["MedicalHistory | None"] = relationship(
        back_populates="visit",
        uselist=False,
    )


class Symptom(Base):
    __tablename__ = "symptoms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient_links: Mapped[list["PatientSymptom"]] = relationship(
        back_populates="symptom",
        cascade="all, delete-orphan",
    )


class PatientSymptom(Base):
    __tablename__ = "patient_symptoms"
    __table_args__ = (
        UniqueConstraint("patient_id", "symptom_id", name="uq_patient_symptom"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    symptom_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("symptoms.id", ondelete="CASCADE"),
        index=True,
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
    )
    last_recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
    )

    patient: Mapped[PatientProfile] = relationship(back_populates="symptom_links")
    symptom: Mapped[Symptom] = relationship(back_populates="patient_links")


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"
    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_doctor_schedule_slot",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    doctor_clinic_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("doctor_clinics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    day_of_week: Mapped[str] = mapped_column(String(20), index=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=30)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    doctor: Mapped[DoctorProfile] = relationship(back_populates="schedules")
    doctor_clinic: Mapped[DoctorClinic | None] = relationship(
        back_populates="schedules"
    )
    slots: Mapped[list["AppointmentSlot"]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
    )


class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"
    __table_args__ = (
        UniqueConstraint(
            "doctor_clinic_id",
            "start_at",
            "end_at",
            name="uq_doctor_clinic_slot_window",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doctor_clinic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctor_clinics.id", ondelete="CASCADE"),
        index=True,
    )
    schedule_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("doctor_schedules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    doctor_clinic: Mapped[DoctorClinic] = relationship(back_populates="slots")
    schedule: Mapped[DoctorSchedule | None] = relationship(back_populates="slots")
    appointment: Mapped[Appointment | None] = relationship(back_populates="slot")


class MedicalHistory(Base):
    __tablename__ = "medical_history"

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
    visit_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("visits.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    appointment_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), default="visit", index=True)
    condition_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    symptoms_summary: Mapped[str] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    prescriptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    vitals: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    attachments: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    patient: Mapped[PatientProfile] = relationship(back_populates="medical_history")
    doctor: Mapped[DoctorProfile | None] = relationship(
        back_populates="medical_history_entries"
    )
    visit: Mapped[Visit | None] = relationship(back_populates="medical_history_entry")
    appointment: Mapped[Appointment | None] = relationship(
        back_populates="medical_history_entries"
    )


class PatientMedicalHistoryEntry(Base):
    __tablename__ = "patient_medical_history_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    category: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(200))
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    patient: Mapped[PatientProfile] = relationship(back_populates="structured_history")


class PatientLabResult(Base):
    __tablename__ = "patient_lab_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    lab_name: Mapped[str] = mapped_column(String(120), index=True)
    value: Mapped[str] = mapped_column(String(60))
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[PatientProfile | None] = relationship(back_populates="lab_results")


class TriageAssessment(Base):
    __tablename__ = "triage_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    appointment_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text)
    triage_level: Mapped[str] = mapped_column(String(20), index=True)
    urgency_level: Mapped[str] = mapped_column(String(20), index=True)
    urgency_label: Mapped[str] = mapped_column(String(200))
    urgency_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    clinical_summary: Mapped[str] = mapped_column(Text)
    simple_reasoning: Mapped[str] = mapped_column(Text)
    plain_language_explanation: Mapped[str] = mapped_column(Text)
    patient_friendly_explanation: Mapped[str] = mapped_column(Text)
    actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommended_actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    red_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommended_specialty: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    specialty_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspected_condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    suspected_conditions: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list
    )
    suggested_doctors: Mapped[list[dict[str, str | int | None]]] = mapped_column(
        JSON,
        default=list,
    )
    supporting_references: Mapped[list[dict[str, str | None]]] = mapped_column(
        JSON,
        default=list,
    )
    disclaimer: Mapped[str] = mapped_column(Text)
    history_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[PatientProfile] = relationship(back_populates="triage_assessments")
    appointment: Mapped[Appointment | None] = relationship(
        back_populates="triage_assessment"
    )
