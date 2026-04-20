"""add patient national id and derived location fields

Revision ID: 0003_add_patient_identity_fields
Revises: 0002_add_prototype_doctors
Create Date: 2026-04-20 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_add_patient_identity_fields"
down_revision = "0002_add_prototype_doctors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patient_profiles",
        sa.Column("national_id", sa.String(length=14), nullable=True),
    )
    op.add_column(
        "patient_profiles",
        sa.Column("date_of_birth", sa.Date(), nullable=True),
    )
    op.add_column(
        "patient_profiles",
        sa.Column("inferred_governorate_code", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "patient_profiles",
        sa.Column("inferred_governorate", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "patient_profiles",
        sa.Column("current_governorate", sa.String(length=120), nullable=True),
    )
    op.create_index(
        op.f("ix_patient_profiles_national_id"),
        "patient_profiles",
        ["national_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_patient_profiles_national_id"), table_name="patient_profiles")
    op.drop_column("patient_profiles", "current_governorate")
    op.drop_column("patient_profiles", "inferred_governorate")
    op.drop_column("patient_profiles", "inferred_governorate_code")
    op.drop_column("patient_profiles", "date_of_birth")
    op.drop_column("patient_profiles", "national_id")
