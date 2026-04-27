"""normalize clinical schema with departments, schedules, symptoms, history, and triage

Revision ID: 0005_normalize_clinical_schema
Revises: 0004_doctor_directory_fields_and_cleanup
Create Date: 2026-04-27 00:00:00.000000
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0005_normalize_clinical_schema"
down_revision = "0004_doctor_directory_fields_and_cleanup"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _extract_symptom_keywords(text_value: str) -> list[str]:
    lowered = (text_value or "").lower()
    keywords = (
        "chest pain",
        "shortness of breath",
        "cough",
        "fever",
        "headache",
        "dizziness",
        "rash",
        "vomiting",
        "abdominal pain",
        "anxiety",
    )
    return [keyword for keyword in keywords if keyword in lowered]


def _insert_and_get_id(
    bind: sa.engine.Connection,
    insert_stmt: sa.Insert,
    id_column: sa.ColumnElement[int],
) -> int:
    result = bind.execute(insert_stmt.returning(id_column))
    return int(result.scalar_one())


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    metadata.bind = bind

    if "departments" not in _table_names():
        op.create_table(
            "departments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_departments_id"), "departments", ["id"], unique=False)
        op.create_index(
            op.f("ix_departments_name"),
            "departments",
            ["name"],
            unique=True,
        )

    with op.batch_alter_table("doctor_profiles") as batch_op:
        if "department_id" not in _column_names("doctor_profiles"):
            batch_op.add_column(sa.Column("department_id", sa.Integer(), nullable=True))
            batch_op.create_index(
                op.f("ix_doctor_profiles_department_id"),
                ["department_id"],
                unique=False,
            )
            batch_op.create_foreign_key(
                "fk_doctor_profiles_department_id_departments",
                "departments",
                ["department_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "doctor_schedules" not in _table_names():
        op.create_table(
            "doctor_schedules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("doctor_id", sa.Integer(), nullable=False),
            sa.Column("day_of_week", sa.String(length=20), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("location_label", sa.String(length=200), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["doctor_id"],
                ["doctor_profiles.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "doctor_id",
                "day_of_week",
                "start_time",
                "end_time",
                name="uq_doctor_schedule_slot",
            ),
        )
        op.create_index(
            op.f("ix_doctor_schedules_day_of_week"),
            "doctor_schedules",
            ["day_of_week"],
            unique=False,
        )
        op.create_index(
            op.f("ix_doctor_schedules_doctor_id"),
            "doctor_schedules",
            ["doctor_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_doctor_schedules_id"),
            "doctor_schedules",
            ["id"],
            unique=False,
        )

    if "symptoms" not in _table_names():
        op.create_table(
            "symptoms",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("category", sa.String(length=120), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_symptoms_id"), "symptoms", ["id"], unique=False)
        op.create_index(op.f("ix_symptoms_name"), "symptoms", ["name"], unique=True)

    if "patient_symptoms" not in _table_names():
        op.create_table(
            "patient_symptoms",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=False),
            sa.Column("symptom_id", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=50), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("first_recorded_at", sa.DateTime(), nullable=False),
            sa.Column("last_recorded_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["patient_id"],
                ["patient_profiles.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["symptom_id"],
                ["symptoms.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "patient_id",
                "symptom_id",
                name="uq_patient_symptom",
            ),
        )
        op.create_index(
            op.f("ix_patient_symptoms_id"),
            "patient_symptoms",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_patient_symptoms_patient_id"),
            "patient_symptoms",
            ["patient_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_patient_symptoms_symptom_id"),
            "patient_symptoms",
            ["symptom_id"],
            unique=False,
        )

    with op.batch_alter_table("visits") as batch_op:
        if "appointment_id" not in _column_names("visits"):
            batch_op.add_column(sa.Column("appointment_id", sa.Integer(), nullable=True))
            batch_op.create_index(
                op.f("ix_visits_appointment_id"),
                ["appointment_id"],
                unique=False,
            )
            batch_op.create_foreign_key(
                "fk_visits_appointment_id_appointments",
                "appointments",
                ["appointment_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "medical_history" not in _table_names():
        op.create_table(
            "medical_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=False),
            sa.Column("doctor_id", sa.Integer(), nullable=True),
            sa.Column("visit_id", sa.Integer(), nullable=True),
            sa.Column("appointment_id", sa.Integer(), nullable=True),
            sa.Column("source_type", sa.String(length=50), nullable=False),
            sa.Column("condition_name", sa.String(length=200), nullable=True),
            sa.Column("symptoms_summary", sa.Text(), nullable=False),
            sa.Column("diagnosis", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("prescriptions", sa.Text(), nullable=True),
            sa.Column("vitals", sa.JSON(), nullable=True),
            sa.Column("attachments", sa.JSON(), nullable=True),
            sa.Column("recorded_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["appointment_id"],
                ["appointments.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["doctor_id"],
                ["doctor_profiles.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["patient_id"],
                ["patient_profiles.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["visit_id"],
                ["visits.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("visit_id"),
        )
        op.create_index(
            op.f("ix_medical_history_id"),
            "medical_history",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_medical_history_patient_id"),
            "medical_history",
            ["patient_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_medical_history_doctor_id"),
            "medical_history",
            ["doctor_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_medical_history_visit_id"),
            "medical_history",
            ["visit_id"],
            unique=True,
        )
        op.create_index(
            op.f("ix_medical_history_appointment_id"),
            "medical_history",
            ["appointment_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_medical_history_source_type"),
            "medical_history",
            ["source_type"],
            unique=False,
        )

    if "triage_assessments" not in _table_names():
        op.create_table(
            "triage_assessments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=False),
            sa.Column("appointment_id", sa.Integer(), nullable=True),
            sa.Column("query_text", sa.Text(), nullable=False),
            sa.Column("triage_level", sa.String(length=20), nullable=False),
            sa.Column("urgency_level", sa.String(length=20), nullable=False),
            sa.Column("urgency_label", sa.String(length=200), nullable=False),
            sa.Column("urgency_reason", sa.Text(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("clinical_summary", sa.Text(), nullable=False),
            sa.Column("simple_reasoning", sa.Text(), nullable=False),
            sa.Column("plain_language_explanation", sa.Text(), nullable=False),
            sa.Column("patient_friendly_explanation", sa.Text(), nullable=False),
            sa.Column("actions", sa.JSON(), nullable=False),
            sa.Column("recommended_actions", sa.JSON(), nullable=False),
            sa.Column("red_flags", sa.JSON(), nullable=False),
            sa.Column("recommended_specialty", sa.String(length=120), nullable=True),
            sa.Column("specialty_reason", sa.Text(), nullable=True),
            sa.Column("suspected_condition", sa.String(length=200), nullable=True),
            sa.Column("suspected_conditions", sa.JSON(), nullable=False),
            sa.Column("suggested_doctors", sa.JSON(), nullable=False),
            sa.Column("supporting_references", sa.JSON(), nullable=False),
            sa.Column("disclaimer", sa.Text(), nullable=False),
            sa.Column("history_used", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["appointment_id"],
                ["appointments.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["patient_id"],
                ["patient_profiles.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("appointment_id"),
        )
        op.create_index(
            op.f("ix_triage_assessments_id"),
            "triage_assessments",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_triage_assessments_patient_id"),
            "triage_assessments",
            ["patient_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_triage_assessments_appointment_id"),
            "triage_assessments",
            ["appointment_id"],
            unique=True,
        )
        op.create_index(
            op.f("ix_triage_assessments_triage_level"),
            "triage_assessments",
            ["triage_level"],
            unique=False,
        )
        op.create_index(
            op.f("ix_triage_assessments_urgency_level"),
            "triage_assessments",
            ["urgency_level"],
            unique=False,
        )

    departments = sa.table(
        "departments",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    doctors = sa.table(
        "doctor_profiles",
        sa.column("id", sa.Integer()),
        sa.column("specialty", sa.String()),
        sa.column("department_id", sa.Integer()),
    )
    visits = sa.table(
        "visits",
        sa.column("id", sa.Integer()),
        sa.column("patient_id", sa.Integer()),
        sa.column("doctor_id", sa.Integer()),
        sa.column("appointment_id", sa.Integer()),
        sa.column("symptoms", sa.Text()),
        sa.column("diagnosis", sa.Text()),
        sa.column("notes", sa.Text()),
        sa.column("prescriptions", sa.Text()),
        sa.column("vitals", sa.JSON()),
        sa.column("attachments", sa.JSON()),
        sa.column("created_at", sa.DateTime()),
    )
    appointments = sa.table(
        "appointments",
        sa.column("id", sa.Integer()),
        sa.column("patient_id", sa.Integer()),
        sa.column("doctor_id", sa.Integer()),
        sa.column("scheduled_for", sa.DateTime()),
        sa.column("status", sa.String()),
    )
    medical_history = sa.table(
        "medical_history",
        sa.column("id", sa.Integer()),
        sa.column("patient_id", sa.Integer()),
        sa.column("doctor_id", sa.Integer()),
        sa.column("visit_id", sa.Integer()),
        sa.column("appointment_id", sa.Integer()),
        sa.column("source_type", sa.String()),
        sa.column("condition_name", sa.String()),
        sa.column("symptoms_summary", sa.Text()),
        sa.column("diagnosis", sa.Text()),
        sa.column("notes", sa.Text()),
        sa.column("prescriptions", sa.Text()),
        sa.column("vitals", sa.JSON()),
        sa.column("attachments", sa.JSON()),
        sa.column("recorded_at", sa.DateTime()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    symptoms = sa.table(
        "symptoms",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("category", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime()),
    )
    patient_symptoms = sa.table(
        "patient_symptoms",
        sa.column("patient_id", sa.Integer()),
        sa.column("symptom_id", sa.Integer()),
        sa.column("source", sa.String()),
        sa.column("notes", sa.Text()),
        sa.column("first_recorded_at", sa.DateTime()),
        sa.column("last_recorded_at", sa.DateTime()),
    )

    now = datetime.now(UTC).replace(tzinfo=None)
    specialty_rows = bind.execute(
        sa.select(doctors.c.id, doctors.c.specialty).where(
            doctors.c.specialty.is_not(None)
        )
    ).all()
    existing_departments = {
        row.name: row.id
        for row in bind.execute(sa.select(departments.c.id, departments.c.name)).all()
    }

    for specialty_row in specialty_rows:
        specialty = (specialty_row.specialty or "").strip()
        if not specialty or specialty in existing_departments:
            continue
        existing_departments[specialty] = _insert_and_get_id(
            bind,
            departments.insert().values(
                name=specialty,
                description=f"{specialty} department",
                created_at=now,
                updated_at=now,
            ),
            departments.c.id,
        )

    for specialty_row in specialty_rows:
        specialty = (specialty_row.specialty or "").strip()
        if not specialty:
            continue
        bind.execute(
            doctors.update()
            .where(doctors.c.id == specialty_row.id)
            .values(department_id=existing_departments.get(specialty))
        )

    visit_rows = bind.execute(sa.select(visits)).all()
    appointment_rows = bind.execute(sa.select(appointments)).all()
    visit_history_count = bind.execute(
        sa.select(sa.func.count()).select_from(medical_history)
    ).scalar_one()

    appointment_candidates: dict[tuple[int, int | None], list[sa.Row]] = {}
    for appointment_row in appointment_rows:
        key = (appointment_row.patient_id, appointment_row.doctor_id)
        appointment_candidates.setdefault(key, []).append(appointment_row)

    for visit_row in visit_rows:
        appointment_id = visit_row.appointment_id
        if appointment_id is None:
            candidates = appointment_candidates.get(
                (visit_row.patient_id, visit_row.doctor_id),
                [],
            )
            if candidates and visit_row.created_at is not None:
                appointment_id = min(
                    candidates,
                    key=lambda item: abs(
                        (
                            (item.scheduled_for or visit_row.created_at)
                            - visit_row.created_at
                        ).total_seconds()
                    ),
                ).id
                bind.execute(
                    visits.update()
                    .where(visits.c.id == visit_row.id)
                    .values(appointment_id=appointment_id)
                )

        exists = bind.execute(
            sa.select(medical_history.c.id).where(medical_history.c.visit_id == visit_row.id)
        ).first()
        if exists is not None:
            continue

        bind.execute(
            medical_history.insert().values(
                patient_id=visit_row.patient_id,
                doctor_id=visit_row.doctor_id,
                visit_id=visit_row.id,
                appointment_id=appointment_id,
                source_type="legacy_visit",
                condition_name=visit_row.diagnosis,
                symptoms_summary=visit_row.symptoms,
                diagnosis=visit_row.diagnosis,
                notes=visit_row.notes,
                prescriptions=visit_row.prescriptions,
                vitals=visit_row.vitals,
                attachments=visit_row.attachments,
                recorded_at=visit_row.created_at or now,
                created_at=now,
                updated_at=now,
            )
        )

        for keyword in _extract_symptom_keywords(visit_row.symptoms or ""):
            symptom_row = bind.execute(
                sa.select(symptoms.c.id).where(symptoms.c.name == keyword)
            ).first()
            if symptom_row is None:
                symptom_id = _insert_and_get_id(
                    bind,
                    symptoms.insert().values(
                        name=keyword,
                        category="legacy_backfill",
                        description=None,
                        created_at=now,
                    ),
                    symptoms.c.id,
                )
            else:
                symptom_id = symptom_row.id

            existing_link = bind.execute(
                sa.select(patient_symptoms.c.patient_id).where(
                    sa.and_(
                        patient_symptoms.c.patient_id == visit_row.patient_id,
                        patient_symptoms.c.symptom_id == symptom_id,
                    )
                )
            ).first()
            if existing_link is not None:
                bind.execute(
                    patient_symptoms.update()
                    .where(
                        sa.and_(
                            patient_symptoms.c.patient_id == visit_row.patient_id,
                            patient_symptoms.c.symptom_id == symptom_id,
                        )
                    )
                    .values(last_recorded_at=visit_row.created_at or now)
                )
                continue

            bind.execute(
                patient_symptoms.insert().values(
                    patient_id=visit_row.patient_id,
                    symptom_id=symptom_id,
                    source="legacy_visit",
                    notes=visit_row.diagnosis,
                    first_recorded_at=visit_row.created_at or now,
                    last_recorded_at=visit_row.created_at or now,
                )
            )

    migrated_history_count = bind.execute(
        sa.select(sa.func.count()).select_from(medical_history)
    ).scalar_one()
    visit_count = bind.execute(sa.select(sa.func.count()).select_from(visits)).scalar_one()
    if migrated_history_count < visit_count and visit_history_count < visit_count:
        raise RuntimeError(
            "Medical history backfill did not preserve all legacy visits."
        )


def downgrade() -> None:
    if "triage_assessments" in _table_names():
        op.drop_index(
            op.f("ix_triage_assessments_urgency_level"),
            table_name="triage_assessments",
        )
        op.drop_index(
            op.f("ix_triage_assessments_triage_level"),
            table_name="triage_assessments",
        )
        op.drop_index(
            op.f("ix_triage_assessments_patient_id"),
            table_name="triage_assessments",
        )
        op.drop_index(
            op.f("ix_triage_assessments_id"),
            table_name="triage_assessments",
        )
        op.drop_index(
            op.f("ix_triage_assessments_appointment_id"),
            table_name="triage_assessments",
        )
        op.drop_table("triage_assessments")

    if "medical_history" in _table_names():
        op.drop_index(op.f("ix_medical_history_source_type"), table_name="medical_history")
        op.drop_index(
            op.f("ix_medical_history_appointment_id"),
            table_name="medical_history",
        )
        op.drop_index(op.f("ix_medical_history_visit_id"), table_name="medical_history")
        op.drop_index(op.f("ix_medical_history_doctor_id"), table_name="medical_history")
        op.drop_index(op.f("ix_medical_history_patient_id"), table_name="medical_history")
        op.drop_index(op.f("ix_medical_history_id"), table_name="medical_history")
        op.drop_table("medical_history")

    with op.batch_alter_table("visits") as batch_op:
        if "appointment_id" in _column_names("visits"):
            batch_op.drop_constraint(
                "fk_visits_appointment_id_appointments",
                type_="foreignkey",
            )
            batch_op.drop_index(op.f("ix_visits_appointment_id"))
            batch_op.drop_column("appointment_id")

    if "patient_symptoms" in _table_names():
        op.drop_index(op.f("ix_patient_symptoms_symptom_id"), table_name="patient_symptoms")
        op.drop_index(op.f("ix_patient_symptoms_patient_id"), table_name="patient_symptoms")
        op.drop_index(op.f("ix_patient_symptoms_id"), table_name="patient_symptoms")
        op.drop_table("patient_symptoms")

    if "symptoms" in _table_names():
        op.drop_index(op.f("ix_symptoms_name"), table_name="symptoms")
        op.drop_index(op.f("ix_symptoms_id"), table_name="symptoms")
        op.drop_table("symptoms")

    if "doctor_schedules" in _table_names():
        op.drop_index(op.f("ix_doctor_schedules_id"), table_name="doctor_schedules")
        op.drop_index(
            op.f("ix_doctor_schedules_doctor_id"),
            table_name="doctor_schedules",
        )
        op.drop_index(
            op.f("ix_doctor_schedules_day_of_week"),
            table_name="doctor_schedules",
        )
        op.drop_table("doctor_schedules")

    with op.batch_alter_table("doctor_profiles") as batch_op:
        if "department_id" in _column_names("doctor_profiles"):
            batch_op.drop_constraint(
                "fk_doctor_profiles_department_id_departments",
                type_="foreignkey",
            )
            batch_op.drop_index(op.f("ix_doctor_profiles_department_id"))
            batch_op.drop_column("department_id")

    if "departments" in _table_names():
        op.drop_index(op.f("ix_departments_name"), table_name="departments")
        op.drop_index(op.f("ix_departments_id"), table_name="departments")
        op.drop_table("departments")
