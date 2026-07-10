"""Add multi-provider AI settings and summary job metadata.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    provider_type = postgresql.ENUM(
        "ollama", "openai", "anthropic", name="ai_provider_type", create_type=False
    )
    language_type = postgresql.ENUM(
        "es", "en", name="summary_language", create_type=False
    )
    status_type = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        "skipped",
        name="ai_summary_status",
        create_type=False,
    )
    postgresql.ENUM(
        "ollama", "openai", "anthropic", name="ai_provider_type"
    ).create(bind, checkfirst=True)
    postgresql.ENUM("es", "en", name="summary_language").create(bind, checkfirst=True)
    postgresql.ENUM(
        "pending", "processing", "completed", "failed", "skipped", name="ai_summary_status"
    ).create(bind, checkfirst=True)

    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", provider_type, nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("summary_language", language_type, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("api_key_hint", sa.String(length=4), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        sa.text(
            "INSERT INTO ai_settings "
            "(id, provider, model, summary_language, enabled, updated_at) "
            "VALUES (1, 'ollama', 'llama3.1:8b', 'es', true, CURRENT_TIMESTAMP)"
        )
    )

    op.add_column("incidents", sa.Column("ai_provider", provider_type, nullable=True))
    op.add_column("incidents", sa.Column("ai_model", sa.String(length=200), nullable=True))
    op.add_column("incidents", sa.Column("ai_status", status_type, nullable=True))
    op.add_column(
        "incidents", sa.Column("ai_attempt_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("incidents", sa.Column("ai_next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("incidents", sa.Column("ai_processing_started_at", sa.DateTime(timezone=True)))
    op.add_column("incidents", sa.Column("ai_last_error_code", sa.String(length=50)))
    op.add_column("incidents", sa.Column("ai_generated_at", sa.DateTime(timezone=True)))
    op.add_column("incidents", sa.Column("ai_input_tokens", sa.Integer()))
    op.add_column("incidents", sa.Column("ai_output_tokens", sa.Integer()))
    op.add_column("incidents", sa.Column("ai_latency_ms", sa.Integer()))
    op.add_column("incidents", sa.Column("prompt_version", sa.Integer()))

    op.execute(
        sa.text(
            "UPDATE incidents SET ai_status = CASE "
            "WHEN ai_summary IS NOT NULL THEN 'completed' ELSE 'skipped' END, "
            "ai_provider = CASE WHEN ai_summary IS NOT NULL THEN 'ollama' ELSE NULL END"
        )
    )
    op.alter_column("incidents", "ai_status", nullable=False)
    op.alter_column("incidents", "ai_attempt_count", server_default=None)
    op.create_index("ix_incidents_ai_status_next", "incidents", ["ai_status", "ai_next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_incidents_ai_status_next", table_name="incidents")
    for column in (
        "prompt_version",
        "ai_latency_ms",
        "ai_output_tokens",
        "ai_input_tokens",
        "ai_generated_at",
        "ai_last_error_code",
        "ai_processing_started_at",
        "ai_next_attempt_at",
        "ai_attempt_count",
        "ai_status",
        "ai_model",
        "ai_provider",
    ):
        op.drop_column("incidents", column)
    op.drop_table("ai_settings")
    bind = op.get_bind()
    sa.Enum(name="ai_summary_status").drop(bind, checkfirst=True)
    sa.Enum(name="summary_language").drop(bind, checkfirst=True)
    sa.Enum(name="ai_provider_type").drop(bind, checkfirst=True)
