"""add care navigation and booking fields

Revision ID: 0008_care_navigation_fields
Revises: 0007_history_labs_scheduling_support
Create Date: 2026-06-20 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_care_navigation_fields"
down_revision = "0007_history_labs_scheduling_support"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column_if_missing(
        "doctor_profiles",
        sa.Column("consultation_fee", sa.Float(), nullable=True),
    )
    _add_column_if_missing(
        "doctor_profiles",
        sa.Column("insurance_providers", sa.JSON(), nullable=True),
    )
    _add_column_if_missing(
        "doctor_profiles",
        sa.Column("payment_methods", sa.JSON(), nullable=True),
    )
    _add_column_if_missing(
        "doctor_profiles",
        sa.Column(
            "offers_telemedicine",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    _add_column_if_missing(
        "appointments",
        sa.Column(
            "visit_type",
            sa.String(length=20),
            server_default="clinic",
            nullable=False,
        ),
    )
    _add_column_if_missing(
        "appointments",
        sa.Column("video_url", sa.String(length=500), nullable=True),
    )
    _add_column_if_missing(
        "visits",
        sa.Column("follow_up_recommendations", sa.JSON(), nullable=True),
    )
    _add_column_if_missing(
        "visits",
        sa.Column("follow_up_due_on", sa.Date(), nullable=True),
    )

    if "doctor_reviews" not in _table_names():
        op.create_table(
            "doctor_reviews",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=False),
            sa.Column("doctor_id", sa.Integer(), nullable=False),
            sa.Column("appointment_id", sa.Integer(), nullable=True),
            sa.Column("visit_id", sa.Integer(), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
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
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["patient_id"],
                ["patient_profiles.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_doctor_reviews_id"), "doctor_reviews", ["id"])
        op.create_index(
            op.f("ix_doctor_reviews_patient_id"),
            "doctor_reviews",
            ["patient_id"],
        )
        op.create_index(
            op.f("ix_doctor_reviews_doctor_id"),
            "doctor_reviews",
            ["doctor_id"],
        )
        op.create_index(
            op.f("ix_doctor_reviews_appointment_id"),
            "doctor_reviews",
            ["appointment_id"],
        )
        op.create_index(
            op.f("ix_doctor_reviews_visit_id"),
            "doctor_reviews",
            ["visit_id"],
        )


def downgrade() -> None:
    if "doctor_reviews" in _table_names():
        op.drop_index(op.f("ix_doctor_reviews_visit_id"), table_name="doctor_reviews")
        op.drop_index(
            op.f("ix_doctor_reviews_appointment_id"),
            table_name="doctor_reviews",
        )
        op.drop_index(op.f("ix_doctor_reviews_doctor_id"), table_name="doctor_reviews")
        op.drop_index(
            op.f("ix_doctor_reviews_patient_id"),
            table_name="doctor_reviews",
        )
        op.drop_index(op.f("ix_doctor_reviews_id"), table_name="doctor_reviews")
        op.drop_table("doctor_reviews")

    for table_name, column_name in (
        ("visits", "follow_up_due_on"),
        ("visits", "follow_up_recommendations"),
        ("appointments", "video_url"),
        ("appointments", "visit_type"),
        ("doctor_profiles", "offers_telemedicine"),
        ("doctor_profiles", "payment_methods"),
        ("doctor_profiles", "insurance_providers"),
        ("doctor_profiles", "consultation_fee"),
    ):
        if column_name in _columns(table_name):
            op.drop_column(table_name, column_name)
