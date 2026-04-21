"""add doctor directory provenance fields and clean legacy fake doctors

Revision ID: 0004_doctor_directory_fields_and_cleanup
Revises: 0003_add_patient_identity_fields
Create Date: 2026-04-21 11:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_doctor_directory_fields_and_cleanup"
down_revision = "0003_add_patient_identity_fields"
branch_labels = None
depends_on = None

LEGACY_PROTOTYPE_NAMES = (
    "Dr. John Smith",
    "Dr. Sarah Johnson",
    "Dr. Ahmed Hassan",
    "Dr. Maria Garcia",
    "Dr. Michael Chen",
    "Dr. Lisa Anderson",
    "Dr. James Wilson",
    "Dr. Emma Thompson",
    "Dr. Robert Brown",
    "Dr. Patricia Davis",
    "Dr. David Martinez",
    "Dr. Jennifer Lee",
)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()

    _add_column_if_missing(
        "doctor_profiles",
        sa.Column("area", sa.String(length=120), nullable=True),
    )
    _add_column_if_missing(
        "doctor_profiles",
        sa.Column("city", sa.String(length=120), nullable=True),
    )
    _add_column_if_missing(
        "doctor_profiles",
        sa.Column("source_name", sa.String(length=120), nullable=True),
    )
    _add_column_if_missing(
        "doctor_profiles",
        sa.Column("source_url", sa.String(length=500), nullable=True),
    )
    _add_column_if_missing(
        "doctor_profiles",
        sa.Column("booking_url", sa.String(length=500), nullable=True),
    )

    bind.execute(
        sa.text(
            "DELETE FROM doctor_profiles WHERE full_name IN :names"
        ).bindparams(sa.bindparam("names", expanding=True, value=list(LEGACY_PROTOTYPE_NAMES)))
    )

    if _has_column("doctor_profiles", "source_name"):
        bind.execute(
            sa.text(
                "DELETE FROM doctor_profiles WHERE source_name = :source_name"
            ),
            {"source_name": "Egyptian Medical Syndicate Registry"},
        )
    if _has_column("doctor_profiles", "source_url"):
        bind.execute(
            sa.text(
                "DELETE FROM doctor_profiles WHERE source_url = :source_url"
            ),
            {"source_url": "https://doctors.example.com/registry"},
        )


def downgrade() -> None:
    if _has_column("doctor_profiles", "booking_url"):
        op.drop_column("doctor_profiles", "booking_url")
    if _has_column("doctor_profiles", "source_url"):
        op.drop_column("doctor_profiles", "source_url")
    if _has_column("doctor_profiles", "source_name"):
        op.drop_column("doctor_profiles", "source_name")
    if _has_column("doctor_profiles", "city"):
        op.drop_column("doctor_profiles", "city")
    if _has_column("doctor_profiles", "area"):
        op.drop_column("doctor_profiles", "area")
