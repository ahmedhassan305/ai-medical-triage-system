"""add clinic and slot booking foundation

Revision ID: 0006_add_slot_booking_foundation
Revises: 0005_normalize_clinical_schema
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0006_add_slot_booking_foundation"
down_revision = "0005_normalize_clinical_schema"
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


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC).replace(tzinfo=None)

    if "clinics" not in _table_names():
        op.create_table(
            "clinics",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("area", sa.String(length=120), nullable=True),
            sa.Column("city", sa.String(length=120), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_clinics_id"), "clinics", ["id"], unique=False)
        op.create_index(op.f("ix_clinics_name"), "clinics", ["name"], unique=False)
        op.create_index(
            op.f("ix_clinics_is_active"),
            "clinics",
            ["is_active"],
            unique=False,
        )

    if "doctor_clinics" not in _table_names():
        op.create_table(
            "doctor_clinics",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("doctor_id", sa.Integer(), nullable=False),
            sa.Column("clinic_id", sa.Integer(), nullable=False),
            sa.Column("scope_at_clinic", sa.String(length=120), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["clinic_id"],
                ["clinics.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["doctor_id"],
                ["doctor_profiles.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "doctor_id",
                "clinic_id",
                name="uq_doctor_clinic_link",
            ),
        )
        op.create_index(
            op.f("ix_doctor_clinics_id"),
            "doctor_clinics",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_doctor_clinics_doctor_id"),
            "doctor_clinics",
            ["doctor_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_doctor_clinics_clinic_id"),
            "doctor_clinics",
            ["clinic_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_doctor_clinics_is_primary"),
            "doctor_clinics",
            ["is_primary"],
            unique=False,
        )
        op.create_index(
            op.f("ix_doctor_clinics_is_active"),
            "doctor_clinics",
            ["is_active"],
            unique=False,
        )

    with op.batch_alter_table("doctor_schedules") as batch_op:
        existing_columns = _column_names("doctor_schedules")
        if "doctor_clinic_id" not in existing_columns:
            batch_op.add_column(
                sa.Column("doctor_clinic_id", sa.Integer(), nullable=True)
            )
            batch_op.create_index(
                op.f("ix_doctor_schedules_doctor_clinic_id"),
                ["doctor_clinic_id"],
                unique=False,
            )
            batch_op.create_foreign_key(
                "fk_doctor_schedules_doctor_clinic_id_doctor_clinics",
                "doctor_clinics",
                ["doctor_clinic_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "slot_minutes" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "slot_minutes", sa.Integer(), nullable=False, server_default="30"
                )
            )
        if "valid_from" not in existing_columns:
            batch_op.add_column(sa.Column("valid_from", sa.Date(), nullable=True))
        if "valid_to" not in existing_columns:
            batch_op.add_column(sa.Column("valid_to", sa.Date(), nullable=True))

    if "appointment_slots" not in _table_names():
        op.create_table(
            "appointment_slots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("doctor_clinic_id", sa.Integer(), nullable=False),
            sa.Column("schedule_id", sa.Integer(), nullable=True),
            sa.Column("start_at", sa.DateTime(), nullable=False),
            sa.Column("end_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["doctor_clinic_id"],
                ["doctor_clinics.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["schedule_id"],
                ["doctor_schedules.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "doctor_clinic_id",
                "start_at",
                "end_at",
                name="uq_doctor_clinic_slot_window",
            ),
        )
        op.create_index(
            op.f("ix_appointment_slots_id"),
            "appointment_slots",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_appointment_slots_doctor_clinic_id"),
            "appointment_slots",
            ["doctor_clinic_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_appointment_slots_schedule_id"),
            "appointment_slots",
            ["schedule_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_appointment_slots_start_at"),
            "appointment_slots",
            ["start_at"],
            unique=False,
        )
        op.create_index(
            op.f("ix_appointment_slots_end_at"),
            "appointment_slots",
            ["end_at"],
            unique=False,
        )
        op.create_index(
            op.f("ix_appointment_slots_status"),
            "appointment_slots",
            ["status"],
            unique=False,
        )

    with op.batch_alter_table("appointments") as batch_op:
        existing_columns = _column_names("appointments")
        if "clinic_id" not in existing_columns:
            batch_op.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
            batch_op.create_index(
                op.f("ix_appointments_clinic_id"),
                ["clinic_id"],
                unique=False,
            )
            batch_op.create_foreign_key(
                "fk_appointments_clinic_id_clinics",
                "clinics",
                ["clinic_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "slot_id" not in existing_columns:
            batch_op.add_column(sa.Column("slot_id", sa.Integer(), nullable=True))
            batch_op.create_index(
                op.f("ix_appointments_slot_id"),
                ["slot_id"],
                unique=True,
            )
            batch_op.create_foreign_key(
                "fk_appointments_slot_id_appointment_slots",
                "appointment_slots",
                ["slot_id"],
                ["id"],
                ondelete="SET NULL",
            )

    clinics = sa.table(
        "clinics",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("address", sa.String()),
        sa.column("area", sa.String()),
        sa.column("city", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    doctor_profiles = sa.table(
        "doctor_profiles",
        sa.column("id", sa.Integer()),
        sa.column("clinic", sa.String()),
        sa.column("area", sa.String()),
        sa.column("city", sa.String()),
    )
    doctor_clinics = sa.table(
        "doctor_clinics",
        sa.column("id", sa.Integer()),
        sa.column("doctor_id", sa.Integer()),
        sa.column("clinic_id", sa.Integer()),
        sa.column("scope_at_clinic", sa.String()),
        sa.column("is_primary", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    doctor_schedules = sa.table(
        "doctor_schedules",
        sa.column("id", sa.Integer()),
        sa.column("doctor_id", sa.Integer()),
        sa.column("doctor_clinic_id", sa.Integer()),
        sa.column("location_label", sa.String()),
    )
    appointments = sa.table(
        "appointments",
        sa.column("id", sa.Integer()),
        sa.column("doctor_id", sa.Integer()),
        sa.column("clinic_id", sa.Integer()),
    )

    clinic_cache: dict[tuple[str, str | None, str | None], int] = {}
    existing_clinics = bind.execute(
        sa.select(
            clinics.c.id,
            clinics.c.name,
            clinics.c.area,
            clinics.c.city,
        )
    ).all()
    for clinic_row in existing_clinics:
        clinic_cache[(clinic_row.name, clinic_row.area, clinic_row.city)] = (
            clinic_row.id
        )

    primary_clinic_by_doctor: dict[int, int] = {}
    doctor_rows = bind.execute(
        sa.select(
            doctor_profiles.c.id,
            doctor_profiles.c.clinic,
            doctor_profiles.c.area,
            doctor_profiles.c.city,
        )
    ).all()
    for doctor_row in doctor_rows:
        clinic_name = (doctor_row.clinic or "").strip()
        if not clinic_name:
            continue
        cache_key = (clinic_name, doctor_row.area, doctor_row.city)
        clinic_id = clinic_cache.get(cache_key)
        if clinic_id is None:
            clinic_id = int(
                bind.execute(
                    clinics.insert()
                    .values(
                        name=clinic_name,
                        address=None,
                        area=doctor_row.area,
                        city=doctor_row.city,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                    .returning(clinics.c.id)
                ).scalar_one()
            )
            clinic_cache[cache_key] = clinic_id

        existing_link = bind.execute(
            sa.select(doctor_clinics.c.id).where(
                sa.and_(
                    doctor_clinics.c.doctor_id == doctor_row.id,
                    doctor_clinics.c.clinic_id == clinic_id,
                )
            )
        ).first()
        if existing_link is None:
            bind.execute(
                doctor_clinics.insert().values(
                    doctor_id=doctor_row.id,
                    clinic_id=clinic_id,
                    scope_at_clinic=None,
                    is_primary=True,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        primary_clinic_by_doctor[doctor_row.id] = clinic_id

    doctor_clinic_rows = bind.execute(
        sa.select(
            doctor_clinics.c.id,
            doctor_clinics.c.doctor_id,
            doctor_clinics.c.clinic_id,
            clinics.c.name,
        ).select_from(
            doctor_clinics.join(clinics, doctor_clinics.c.clinic_id == clinics.c.id)
        )
    ).all()
    doctor_clinic_by_name: dict[tuple[int, str], int] = {}
    default_doctor_clinic: dict[int, int] = {}
    for link_row in doctor_clinic_rows:
        default_doctor_clinic.setdefault(link_row.doctor_id, link_row.id)
        doctor_clinic_by_name[
            (link_row.doctor_id, (link_row.name or "").strip().lower())
        ] = link_row.id

    schedule_rows = bind.execute(
        sa.select(
            doctor_schedules.c.id,
            doctor_schedules.c.doctor_id,
            doctor_schedules.c.doctor_clinic_id,
            doctor_schedules.c.location_label,
        )
    ).all()
    for schedule_row in schedule_rows:
        if schedule_row.doctor_clinic_id is not None:
            continue
        location_key = (schedule_row.location_label or "").strip().lower()
        doctor_clinic_id = None
        if location_key:
            doctor_clinic_id = doctor_clinic_by_name.get(
                (schedule_row.doctor_id, location_key)
            )
        if doctor_clinic_id is None:
            doctor_clinic_id = default_doctor_clinic.get(schedule_row.doctor_id)
        if doctor_clinic_id is None:
            continue
        bind.execute(
            doctor_schedules.update()
            .where(doctor_schedules.c.id == schedule_row.id)
            .values(doctor_clinic_id=doctor_clinic_id)
        )

    appointment_rows = bind.execute(
        sa.select(appointments.c.id, appointments.c.doctor_id, appointments.c.clinic_id)
    ).all()
    for appointment_row in appointment_rows:
        if appointment_row.clinic_id is not None:
            continue
        clinic_id = primary_clinic_by_doctor.get(appointment_row.doctor_id)
        if clinic_id is None:
            continue
        bind.execute(
            appointments.update()
            .where(appointments.c.id == appointment_row.id)
            .values(clinic_id=clinic_id)
        )


def downgrade() -> None:
    with op.batch_alter_table("appointments") as batch_op:
        existing_columns = _column_names("appointments")
        if "slot_id" in existing_columns:
            batch_op.drop_constraint(
                "fk_appointments_slot_id_appointment_slots",
                type_="foreignkey",
            )
            batch_op.drop_index(op.f("ix_appointments_slot_id"))
            batch_op.drop_column("slot_id")
        if "clinic_id" in existing_columns:
            batch_op.drop_constraint(
                "fk_appointments_clinic_id_clinics",
                type_="foreignkey",
            )
            batch_op.drop_index(op.f("ix_appointments_clinic_id"))
            batch_op.drop_column("clinic_id")

    if "appointment_slots" in _table_names():
        op.drop_index(
            op.f("ix_appointment_slots_status"), table_name="appointment_slots"
        )
        op.drop_index(
            op.f("ix_appointment_slots_end_at"), table_name="appointment_slots"
        )
        op.drop_index(
            op.f("ix_appointment_slots_start_at"), table_name="appointment_slots"
        )
        op.drop_index(
            op.f("ix_appointment_slots_schedule_id"),
            table_name="appointment_slots",
        )
        op.drop_index(
            op.f("ix_appointment_slots_doctor_clinic_id"),
            table_name="appointment_slots",
        )
        op.drop_index(op.f("ix_appointment_slots_id"), table_name="appointment_slots")
        op.drop_table("appointment_slots")

    with op.batch_alter_table("doctor_schedules") as batch_op:
        existing_columns = _column_names("doctor_schedules")
        if "valid_to" in existing_columns:
            batch_op.drop_column("valid_to")
        if "valid_from" in existing_columns:
            batch_op.drop_column("valid_from")
        if "slot_minutes" in existing_columns:
            batch_op.drop_column("slot_minutes")
        if "doctor_clinic_id" in existing_columns:
            batch_op.drop_constraint(
                "fk_doctor_schedules_doctor_clinic_id_doctor_clinics",
                type_="foreignkey",
            )
            batch_op.drop_index(op.f("ix_doctor_schedules_doctor_clinic_id"))
            batch_op.drop_column("doctor_clinic_id")

    if "doctor_clinics" in _table_names():
        op.drop_index(op.f("ix_doctor_clinics_is_active"), table_name="doctor_clinics")
        op.drop_index(op.f("ix_doctor_clinics_is_primary"), table_name="doctor_clinics")
        op.drop_index(op.f("ix_doctor_clinics_clinic_id"), table_name="doctor_clinics")
        op.drop_index(op.f("ix_doctor_clinics_doctor_id"), table_name="doctor_clinics")
        op.drop_index(op.f("ix_doctor_clinics_id"), table_name="doctor_clinics")
        op.drop_table("doctor_clinics")

    if "clinics" in _table_names():
        op.drop_index(op.f("ix_clinics_is_active"), table_name="clinics")
        op.drop_index(op.f("ix_clinics_name"), table_name="clinics")
        op.drop_index(op.f("ix_clinics_id"), table_name="clinics")
        op.drop_table("clinics")
