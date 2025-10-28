"""Initial schema for tenants and lock audit

Revision ID: 0001_initial
Revises: 
Create Date: 2025-10-27 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tenants_tenant_id", "tenants", ["tenant_id"], unique=True)
    op.create_index("ix_tenants_status", "tenants", ["status"], unique=False)

    # tenant_user_identifiers table
    op.create_table(
        "tenant_user_identifiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("identifier", name="uq_identifier"),
    )
    op.create_index("ix_tenant_user_identifiers_tenant_id", "tenant_user_identifiers", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_user_identifiers_identifier", "tenant_user_identifiers", ["identifier"], unique=False)

    # lock_audit table
    op.create_table(
        "lock_audit",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("lock_key", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
    )
    op.create_index("ix_lock_audit_lock_key", "lock_audit", ["lock_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lock_audit_lock_key", table_name="lock_audit")
    op.drop_table("lock_audit")

    op.drop_index("ix_tenant_user_identifiers_identifier", table_name="tenant_user_identifiers")
    op.drop_index("ix_tenant_user_identifiers_tenant_id", table_name="tenant_user_identifiers")
    op.drop_table("tenant_user_identifiers")

    op.drop_index("ix_tenants_status", table_name="tenants")
    op.drop_index("ix_tenants_tenant_id", table_name="tenants")
    op.drop_table("tenants")
