"""add structured history and lab result support

Revision ID: 0007_history_labs_scheduling_support
Revises: 0006_add_slot_booking_foundation
Create Date: 2026-05-18 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_history_labs_scheduling_support"
down_revision = "0006_add_slot_booking_foundation"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    tables = _table_names()
    if "patient_medical_history_entries" not in tables:
        op.create_table(
            "patient_medical_history_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=60), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("occurred_on", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["patient_id"],
                ["patient_profiles.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_patient_medical_history_entries_id"),
            "patient_medical_history_entries",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_patient_medical_history_entries_patient_id"),
            "patient_medical_history_entries",
            ["patient_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_patient_medical_history_entries_category"),
            "patient_medical_history_entries",
            ["category"],
            unique=False,
        )

    if "patient_lab_results" not in tables:
        op.create_table(
            "patient_lab_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=True),
            sa.Column("lab_name", sa.String(length=120), nullable=False),
            sa.Column("value", sa.String(length=60), nullable=False),
            sa.Column("unit", sa.String(length=40), nullable=True),
            sa.Column("reference_range", sa.String(length=120), nullable=True),
            sa.Column("source_filename", sa.String(length=255), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["patient_id"],
                ["patient_profiles.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_patient_lab_results_id"),
            "patient_lab_results",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_patient_lab_results_patient_id"),
            "patient_lab_results",
            ["patient_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_patient_lab_results_lab_name"),
            "patient_lab_results",
            ["lab_name"],
            unique=False,
        )


def downgrade() -> None:
    tables = _table_names()
    if "patient_lab_results" in tables:
        op.drop_index(op.f("ix_patient_lab_results_lab_name"), table_name="patient_lab_results")
        op.drop_index(op.f("ix_patient_lab_results_patient_id"), table_name="patient_lab_results")
        op.drop_index(op.f("ix_patient_lab_results_id"), table_name="patient_lab_results")
        op.drop_table("patient_lab_results")
    if "patient_medical_history_entries" in tables:
        op.drop_index(
            op.f("ix_patient_medical_history_entries_category"),
            table_name="patient_medical_history_entries",
        )
        op.drop_index(
            op.f("ix_patient_medical_history_entries_patient_id"),
            table_name="patient_medical_history_entries",
        )
        op.drop_index(
            op.f("ix_patient_medical_history_entries_id"),
            table_name="patient_medical_history_entries",
        )
        op.drop_table("patient_medical_history_entries")
