"""Add consented user memory storage without replaying transcripts.

Revision ID: 4e01_user_memory
Revises: 3d01_service_points
"""
from alembic import op
import sqlalchemy as sa

revision = '4e01_user_memory'
down_revision = '3d01_service_points'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('memory_revision', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.create_table('user_memory_facts',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('key', sa.String(64), primary_key=True),
        sa.Column('value', sa.JSON(none_as_null=True), nullable=True),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('source_kind', sa.String(16), nullable=False),
        sa.Column('source_session_id', sa.String(128), nullable=True),
        sa.Column('source_message_id', sa.String(36), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("key IN ('owned_vehicle.model','owned_vehicle.version','owned_vehicle.model_year','owned_vehicle.battery_plan','home_city','registration_city')", name='ck_user_memory_key'),
        sa.CheckConstraint("status IN ('confirmed','unknown','retracted')", name='ck_user_memory_status'),
        sa.CheckConstraint("source_kind IN ('chat','profile')", name='ck_user_memory_source'),
        sa.CheckConstraint("(status = 'confirmed' AND value IS NOT NULL) OR (status IN ('unknown','retracted') AND value IS NULL)", name='ck_user_memory_value_status'),
    )


def downgrade() -> None:
    # Test/local schema rollback only. Production rollback disables the flag/app
    # first and retains this additive schema and its revision fence.
    op.drop_table('user_memory_facts')
    op.drop_column('users', 'memory_revision')
