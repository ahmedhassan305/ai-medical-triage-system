"""add triage audit tables

Revision ID: 0002_triage_audit_tables
Revises: 0001_crm_initial
Create Date: 2026-03-18 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_triage_audit_tables"
down_revision = "0001_crm_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "triage_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("heuristic_level", sa.String(length=20), nullable=False),
        sa.Column("embedding_level", sa.String(length=20), nullable=False),
        sa.Column("llm_level", sa.String(length=20), nullable=True),
        sa.Column("final_level", sa.String(length=20), nullable=False),
        sa.Column("history_used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_triage_sessions_id"),
        "triage_sessions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_triage_sessions_user_id"),
        "triage_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_triage_sessions_patient_id"),
        "triage_sessions",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_triage_sessions_heuristic_level"),
        "triage_sessions",
        ["heuristic_level"],
        unique=False,
    )
    op.create_index(
        op.f("ix_triage_sessions_embedding_level"),
        "triage_sessions",
        ["embedding_level"],
        unique=False,
    )
    op.create_index(
        op.f("ix_triage_sessions_final_level"),
        "triage_sessions",
        ["final_level"],
        unique=False,
    )

    op.create_table(
        "triage_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("triage_session_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("risk_reasoning", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("red_flags", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("decision_payload", sa.JSON(), nullable=False),
        sa.Column("reasoner_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["triage_session_id"], ["triage_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("triage_session_id"),
    )
    op.create_index(
        op.f("ix_triage_results_id"),
        "triage_results",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_triage_results_triage_session_id"),
        "triage_results",
        ["triage_session_id"],
        unique=False,
    )

    op.create_table(
        "retrieved_chunks_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("triage_session_id", sa.Integer(), nullable=False),
        sa.Column("doc_id", sa.String(length=255), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("chunk_id", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["triage_session_id"], ["triage_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_retrieved_chunks_log_id"),
        "retrieved_chunks_log",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_retrieved_chunks_log_triage_session_id"),
        "retrieved_chunks_log",
        ["triage_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_retrieved_chunks_log_doc_id"),
        "retrieved_chunks_log",
        ["doc_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_retrieved_chunks_log_chunk_id"),
        "retrieved_chunks_log",
        ["chunk_id"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_id"),
        "audit_logs",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_user_id"),
        "audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_action"),
        "audit_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_resource_type"),
        "audit_logs",
        ["resource_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_status"),
        "audit_logs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_status"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(
        op.f("ix_retrieved_chunks_log_chunk_id"), table_name="retrieved_chunks_log"
    )
    op.drop_index(
        op.f("ix_retrieved_chunks_log_doc_id"), table_name="retrieved_chunks_log"
    )
    op.drop_index(
        op.f("ix_retrieved_chunks_log_triage_session_id"),
        table_name="retrieved_chunks_log",
    )
    op.drop_index(op.f("ix_retrieved_chunks_log_id"), table_name="retrieved_chunks_log")
    op.drop_table("retrieved_chunks_log")

    op.drop_index(
        op.f("ix_triage_results_triage_session_id"),
        table_name="triage_results",
    )
    op.drop_index(op.f("ix_triage_results_id"), table_name="triage_results")
    op.drop_table("triage_results")

    op.drop_index(op.f("ix_triage_sessions_final_level"), table_name="triage_sessions")
    op.drop_index(
        op.f("ix_triage_sessions_embedding_level"),
        table_name="triage_sessions",
    )
    op.drop_index(
        op.f("ix_triage_sessions_heuristic_level"),
        table_name="triage_sessions",
    )
    op.drop_index(op.f("ix_triage_sessions_patient_id"), table_name="triage_sessions")
    op.drop_index(op.f("ix_triage_sessions_user_id"), table_name="triage_sessions")
    op.drop_index(op.f("ix_triage_sessions_id"), table_name="triage_sessions")
    op.drop_table("triage_sessions")
