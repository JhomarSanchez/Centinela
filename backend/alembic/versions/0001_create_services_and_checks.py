"""Create services and checks tables.

Revision ID: 0001
Revises:
Create Date: 2026-07-07

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("check_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("up", "degraded", "down", name="check_status"),
            nullable=False,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("http_code", sa.Integer(), nullable=True),
    )
    op.create_index("ix_checks_service_id", "checks", ["service_id"])
    op.create_index("ix_checks_checked_at", "checks", ["checked_at"])


def downgrade() -> None:
    op.drop_index("ix_checks_checked_at", table_name="checks")
    op.drop_index("ix_checks_service_id", table_name="checks")
    op.drop_table("checks")
    op.drop_table("services")
    # The enum type is a separate object in PostgreSQL and must be dropped explicitly.
    sa.Enum(name="check_status").drop(op.get_bind(), checkfirst=True)
