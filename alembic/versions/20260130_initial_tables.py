"""Initial tables

Revision ID: 20260130_initial_tables
Revises:
Create Date: 2026-01-30 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260130_initial_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define enum type (don't create since it might already exist)
    user_role_enum = postgresql.ENUM('MASTER_ADMIN', 'SUPER_ADMIN', 'ADMIN', 'SALES_AGENT', 'INVESTOR', name='userrole', create_type=False)

    # Create users table first (without foreign keys to itself initially)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("role", sa.Enum('MASTER_ADMIN', 'SUPER_ADMIN', 'ADMIN', 'SALES_AGENT', 'INVESTOR', name='userrole'), nullable=False),
        sa.Column("status", sa.String(20), default="active", nullable=False),
        sa.Column("builder_id", postgresql.UUID(as_uuid=True)),
        sa.Column("investor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create builders table
    op.create_table(
        "builders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("registration_number", sa.String(100), unique=True),
        sa.Column("contact_person", sa.String(255)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("address", sa.Text),
        sa.Column("city", sa.String(100)),
        sa.Column("country", sa.String(100)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("max_projects", sa.Integer, default=10),
        sa.Column("status", sa.String(20), default="active", nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create investors table
    op.create_table(
        "investors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company_name", sa.String(255)),
        sa.Column("cnic", sa.String(15), unique=True),
        sa.Column("contact_person", sa.String(255)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("address", sa.Text),
        sa.Column("city", sa.String(100)),
        sa.Column("country", sa.String(100)),
        sa.Column("status", sa.String(20), default="active", nullable=False),
        sa.Column("builder_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("builder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("location", sa.Text),
        sa.Column("city", sa.String(100)),
        sa.Column("total_units", sa.Integer),
        sa.Column("status", sa.String(20), default="active", nullable=False),
        sa.Column("start_date", sa.Date),
        sa.Column("expected_completion_date", sa.Date),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create phases_blocks table
    op.create_table(
        "phases_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),  # e.g., "Phase 1", "Block A"
        sa.Column("description", sa.Text),
        sa.Column("total_units", sa.Integer),
        sa.Column("status", sa.String(20), default="active", nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("father_name", sa.String(100)),
        sa.Column("cnic", sa.String(15), unique=True),
        sa.Column("contact_number", sa.String(20), nullable=False),
        sa.Column("alternate_contact", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("address", sa.Text),
        sa.Column("city", sa.String(100)),
        sa.Column("country", sa.String(100)),
        sa.Column("occupation", sa.String(100)),
        sa.Column("status", sa.String(20), default="active", nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create inventory table
    op.create_table(
        "inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phase_block_id", postgresql.UUID(as_uuid=True)),
        sa.Column("unit_number", sa.String(50)),
        sa.Column("unit_type", sa.String(50), nullable=False),  # 'plot', 'file', 'flat', 'villa', 'commercial'
        sa.Column("category", sa.String(50)),  # 'residential', 'commercial', 'agricultural
        sa.Column("size", sa.DECIMAL(10, 2)),  # in square feet or marlas
        sa.Column("price", sa.DECIMAL(15, 2), nullable=False),
        sa.Column("status", sa.String(20), default="available", nullable=False),  # 'available', 'on_hold', 'booked', 'sold'
        sa.Column("hold_expiry_date", sa.DateTime(timezone=True)),
        sa.Column("booked_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("investor_locked", sa.Boolean, default=False),
        sa.Column("investor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("remarks", sa.Text),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create investor_inventory_assignments table
    op.create_table(
        "investor_inventory_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("investor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("percentage_share", sa.DECIMAL(5, 2), nullable=False),  # e.g., 50.00 for 50%
        sa.Column("consent_required", sa.Boolean, default=True),
        sa.Column("status", sa.String(20), default="active", nullable=False),  # 'active', 'inactive'
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create bookings table
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("booking_amount", sa.DECIMAL(15, 2), nullable=False),
        sa.Column("booking_status", sa.String(20), default="confirmed", nullable=False),  # 'confirmed', 'cancelled', 'completed'
        sa.Column("booking_type", sa.String(20), default="sale", nullable=False),  # 'hold', 'booking', 'sale'
        sa.Column("booking_reference", sa.String(100), unique=True),
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("cancelled_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("cancellation_reason", sa.Text),
        sa.Column("cancellation_date", sa.DateTime(timezone=True)),
        sa.Column("remarks", sa.Text),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create payments table
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.DECIMAL(15, 2), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=False),  # 'cash', 'cheque', 'bank_transfer', 'online'
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("reference_number", sa.String(100)),
        sa.Column("cheque_number", sa.String(50)),
        sa.Column("bank_name", sa.String(100)),
        sa.Column("payment_status", sa.String(20), default="received", nullable=False),  # 'received', 'pending', 'rejected'
        sa.Column("remarks", sa.Text),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create installments table
    op.create_table(
        "installments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("installment_number", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount", sa.DECIMAL(15, 2), nullable=False),
        sa.Column("paid_amount", sa.DECIMAL(15, 2), default=0),
        sa.Column("due_status", sa.String(20), default="pending", nullable=False),  # 'pending', 'paid', 'overdue', 'waived'
        sa.Column("paid_date", sa.Date),
        sa.Column("remarks", sa.Text),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create transfers table
    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transfer_date", sa.Date, nullable=False),
        sa.Column("transfer_fee", sa.DECIMAL(10, 2)),
        sa.Column("status", sa.String(20), default="pending", nullable=False),  # 'pending', 'approved', 'rejected', 'completed'
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("remarks", sa.Text),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),  # 'INSERT', 'UPDATE', 'DELETE'
        sa.Column("old_values", postgresql.JSONB),
        sa.Column("new_values", postgresql.JSONB),
        sa.Column("changed_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id")
    )

    # Now add the foreign key constraints
    op.create_foreign_key("fk_users_builder_id", "users", "builders", ["builder_id"], ["id"])
    op.create_foreign_key("fk_users_investor_id", "users", "investors", ["investor_id"], ["id"])
    op.create_foreign_key("fk_users_created_by_id", "users", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_users_updated_by_id", "users", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_builders_created_by_id", "builders", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_builders_updated_by_id", "builders", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_investors_builder_id", "investors", "builders", ["builder_id"], ["id"])
    op.create_foreign_key("fk_investors_created_by_id", "investors", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_investors_updated_by_id", "investors", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_projects_builder_id", "projects", "builders", ["builder_id"], ["id"])
    op.create_foreign_key("fk_projects_created_by_id", "projects", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_projects_updated_by_id", "projects", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_phases_blocks_project_id", "phases_blocks", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_phases_blocks_created_by_id", "phases_blocks", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_phases_blocks_updated_by_id", "phases_blocks", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_customers_created_by_id", "customers", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_customers_updated_by_id", "customers", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_inventory_project_id", "inventory", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_inventory_phase_block_id", "inventory", "phases_blocks", ["phase_block_id"], ["id"])
    op.create_foreign_key("fk_inventory_booked_by_id", "inventory", "users", ["booked_by_id"], ["id"])
    op.create_foreign_key("fk_inventory_investor_id", "inventory", "investors", ["investor_id"], ["id"])
    op.create_foreign_key("fk_inventory_created_by_id", "inventory", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_inventory_updated_by_id", "inventory", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_investor_inventory_assignments_investor_id", "investor_inventory_assignments", "investors", ["investor_id"], ["id"])
    op.create_foreign_key("fk_investor_inventory_assignments_inventory_id", "investor_inventory_assignments", "inventory", ["inventory_id"], ["id"])
    op.create_foreign_key("fk_investor_inventory_assignments_created_by_id", "investor_inventory_assignments", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_investor_inventory_assignments_updated_by_id", "investor_inventory_assignments", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_bookings_inventory_id", "bookings", "inventory", ["inventory_id"], ["id"])
    op.create_foreign_key("fk_bookings_customer_id", "bookings", "customers", ["customer_id"], ["id"])
    op.create_foreign_key("fk_bookings_project_id", "bookings", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_bookings_approved_by_id", "bookings", "users", ["approved_by_id"], ["id"])
    op.create_foreign_key("fk_bookings_cancelled_by_id", "bookings", "users", ["cancelled_by_id"], ["id"])
    op.create_foreign_key("fk_bookings_created_by_id", "bookings", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_bookings_updated_by_id", "bookings", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_payments_booking_id", "payments", "bookings", ["booking_id"], ["id"])
    op.create_foreign_key("fk_payments_customer_id", "payments", "customers", ["customer_id"], ["id"])
    op.create_foreign_key("fk_payments_created_by_id", "payments", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_payments_updated_by_id", "payments", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_installments_booking_id", "installments", "bookings", ["booking_id"], ["id"])
    op.create_foreign_key("fk_installments_created_by_id", "installments", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_installments_updated_by_id", "installments", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_transfers_inventory_id", "transfers", "inventory", ["inventory_id"], ["id"])
    op.create_foreign_key("fk_transfers_booking_id", "transfers", "bookings", ["booking_id"], ["id"])
    op.create_foreign_key("fk_transfers_from_customer_id", "transfers", "customers", ["from_customer_id"], ["id"])
    op.create_foreign_key("fk_transfers_to_customer_id", "transfers", "customers", ["to_customer_id"], ["id"])
    op.create_foreign_key("fk_transfers_approved_by_id", "transfers", "users", ["approved_by_id"], ["id"])
    op.create_foreign_key("fk_transfers_created_by_id", "transfers", "users", ["created_by_id"], ["id"])
    op.create_foreign_key("fk_transfers_updated_by_id", "transfers", "users", ["updated_by_id"], ["id"])

    op.create_foreign_key("fk_audit_logs_changed_by_id", "audit_logs", "users", ["changed_by_id"], ["id"])


def downgrade() -> None:
    # Drop foreign key constraints first
    op.drop_constraint("fk_audit_logs_changed_by_id", "audit_logs", type_="foreignkey")

    op.drop_constraint("fk_transfers_updated_by_id", "transfers", type_="foreignkey")
    op.drop_constraint("fk_transfers_created_by_id", "transfers", type_="foreignkey")
    op.drop_constraint("fk_transfers_approved_by_id", "transfers", type_="foreignkey")
    op.drop_constraint("fk_transfers_to_customer_id", "transfers", type_="foreignkey")
    op.drop_constraint("fk_transfers_from_customer_id", "transfers", type_="foreignkey")
    op.drop_constraint("fk_transfers_booking_id", "transfers", type_="foreignkey")
    op.drop_constraint("fk_transfers_inventory_id", "transfers", type_="foreignkey")

    op.drop_constraint("fk_installments_updated_by_id", "installments", type_="foreignkey")
    op.drop_constraint("fk_installments_created_by_id", "installments", type_="foreignkey")
    op.drop_constraint("fk_installments_booking_id", "installments", type_="foreignkey")

    op.drop_constraint("fk_payments_updated_by_id", "payments", type_="foreignkey")
    op.drop_constraint("fk_payments_created_by_id", "payments", type_="foreignkey")
    op.drop_constraint("fk_payments_customer_id", "payments", type_="foreignkey")
    op.drop_constraint("fk_payments_booking_id", "payments", type_="foreignkey")

    op.drop_constraint("fk_bookings_updated_by_id", "bookings", type_="foreignkey")
    op.drop_constraint("fk_bookings_created_by_id", "bookings", type_="foreignkey")
    op.drop_constraint("fk_bookings_cancelled_by_id", "bookings", type_="foreignkey")
    op.drop_constraint("fk_bookings_approved_by_id", "bookings", type_="foreignkey")
    op.drop_constraint("fk_bookings_project_id", "bookings", type_="foreignkey")
    op.drop_constraint("fk_bookings_customer_id", "bookings", type_="foreignkey")
    op.drop_constraint("fk_bookings_inventory_id", "bookings", type_="foreignkey")

    op.drop_constraint("fk_investor_inventory_assignments_updated_by_id", "investor_inventory_assignments", type_="foreignkey")
    op.drop_constraint("fk_investor_inventory_assignments_created_by_id", "investor_inventory_assignments", type_="foreignkey")
    op.drop_constraint("fk_investor_inventory_assignments_inventory_id", "investor_inventory_assignments", type_="foreignkey")
    op.drop_constraint("fk_investor_inventory_assignments_investor_id", "investor_inventory_assignments", type_="foreignkey")

    op.drop_constraint("fk_inventory_updated_by_id", "inventory", type_="foreignkey")
    op.drop_constraint("fk_inventory_created_by_id", "inventory", type_="foreignkey")
    op.drop_constraint("fk_inventory_investor_id", "inventory", type_="foreignkey")
    op.drop_constraint("fk_inventory_booked_by_id", "inventory", type_="foreignkey")
    op.drop_constraint("fk_inventory_phase_block_id", "inventory", type_="foreignkey")
    op.drop_constraint("fk_inventory_project_id", "inventory", type_="foreignkey")

    op.drop_constraint("fk_customers_updated_by_id", "customers", type_="foreignkey")
    op.drop_constraint("fk_customers_created_by_id", "customers", type_="foreignkey")

    op.drop_constraint("fk_phases_blocks_updated_by_id", "phases_blocks", type_="foreignkey")
    op.drop_constraint("fk_phases_blocks_created_by_id", "phases_blocks", type_="foreignkey")
    op.drop_constraint("fk_phases_blocks_project_id", "phases_blocks", type_="foreignkey")

    op.drop_constraint("fk_projects_updated_by_id", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_created_by_id", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_builder_id", "projects", type_="foreignkey")

    op.drop_constraint("fk_investors_updated_by_id", "investors", type_="foreignkey")
    op.drop_constraint("fk_investors_created_by_id", "investors", type_="foreignkey")
    op.drop_constraint("fk_investors_builder_id", "investors", type_="foreignkey")

    op.drop_constraint("fk_builders_updated_by_id", "builders", type_="foreignkey")
    op.drop_constraint("fk_builders_created_by_id", "builders", type_="foreignkey")

    op.drop_constraint("fk_users_updated_by_id", "users", type_="foreignkey")
    op.drop_constraint("fk_users_created_by_id", "users", type_="foreignkey")
    op.drop_constraint("fk_users_investor_id", "users", type_="foreignkey")
    op.drop_constraint("fk_users_builder_id", "users", type_="foreignkey")

    # Drop tables
    op.drop_table("audit_logs")
    op.drop_table("transfers")
    op.drop_table("installments")
    op.drop_table("payments")
    op.drop_table("bookings")
    op.drop_table("investor_inventory_assignments")
    op.drop_table("inventory")
    op.drop_table("customers")
    op.drop_table("phases_blocks")
    op.drop_table("projects")
    op.drop_table("investors")
    op.drop_table("builders")
    op.drop_table("users")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS userrole CASCADE;")