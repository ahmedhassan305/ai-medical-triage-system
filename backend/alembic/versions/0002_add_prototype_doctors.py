"""Add prototype doctors for testing

Revision ID: 0002_add_prototype_doctors
Revises: 0001_crm_initial
Create Date: 2026-04-18 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from datetime import datetime

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_prototype_doctors"
down_revision = "0001_crm_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add prototype doctors to the doctor_profiles table."""
    doctors_table = sa.table(
        "doctor_profiles",
        sa.column("full_name", sa.String),
        sa.column("specialty", sa.String),
        sa.column("clinic", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    doctors_data = [
        {
            "full_name": "Dr. John Smith",
            "specialty": "Cardiology",
            "clinic": "Heart Care Center",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Sarah Johnson",
            "specialty": "Cardiology",
            "clinic": "City Hospital Cardiology",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Ahmed Hassan",
            "specialty": "Pulmonology",
            "clinic": "Respiratory Health Clinic",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Maria Garcia",
            "specialty": "Pulmonology",
            "clinic": "Lung Care Associates",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Michael Chen",
            "specialty": "Gastroenterology",
            "clinic": "Digestive Health Institute",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Lisa Anderson",
            "specialty": "Gastroenterology",
            "clinic": "Downtown Gastro Clinic",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. James Wilson",
            "specialty": "Neurology",
            "clinic": "Brain & Nerve Center",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Emma Thompson",
            "specialty": "Neurology",
            "clinic": "Neuroscience Institute",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Robert Brown",
            "specialty": "Dermatology",
            "clinic": "Skin Care Specialists",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Patricia Davis",
            "specialty": "Internal Medicine",
            "clinic": "General Health Clinic",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. David Martinez",
            "specialty": "Orthopedics",
            "clinic": "Bone & Joint Center",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "full_name": "Dr. Jennifer Lee",
            "specialty": "Psychiatry",
            "clinic": "Mental Health Associates",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
    ]

    op.bulk_insert(doctors_table, doctors_data)


def downgrade() -> None:
    """Remove prototype doctors."""
    op.execute(
        """
        DELETE FROM doctor_profiles 
        WHERE full_name IN (
            'Dr. John Smith', 'Dr. Sarah Johnson', 'Dr. Ahmed Hassan',
            'Dr. Maria Garcia', 'Dr. Michael Chen', 'Dr. Lisa Anderson',
            'Dr. James Wilson', 'Dr. Emma Thompson', 'Dr. Robert Brown',
            'Dr. Patricia Davis', 'Dr. David Martinez', 'Dr. Jennifer Lee'
        )
    """
    )
