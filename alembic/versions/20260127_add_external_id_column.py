"""Add external_id column to all tables

Revision ID: 20260127_add_external_id
Revises:
Create Date: 2026-01-27 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260127_add_external_id"
down_revision: Union[str, None] = "20260130_initial_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add external_id column to all tables
    op.add_column("users", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("builders", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("projects", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("phases_blocks", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("inventory", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("investors", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("investor_inventory_assignments", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("bookings", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("customers", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("payments", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("installments", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("transfers", sa.Column("external_id", sa.String(50), unique=True))
    op.add_column("audit_logs", sa.Column("external_id", sa.String(50), unique=True))


def downgrade() -> None:
    # Drop external_id column from all tables
    op.drop_column("users", "external_id")
    op.drop_column("builders", "external_id")
    op.drop_column("projects", "external_id")
    op.drop_column("phases_blocks", "external_id")
    op.drop_column("inventory", "external_id")
    op.drop_column("investors", "external_id")
    op.drop_column("investor_inventory_assignments", "external_id")
    op.drop_column("bookings", "external_id")
    op.drop_column("customers", "external_id")
    op.drop_column("payments", "external_id")
    op.drop_column("installments", "external_id")
    op.drop_column("transfers", "external_id")
    op.drop_column("audit_logs", "external_id")