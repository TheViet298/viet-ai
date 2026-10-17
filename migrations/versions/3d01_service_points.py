"""create service_points table

Revision ID: 3d01_service_points
Revises: 2c11_chat_memory
Create Date: 2026-10-17 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d01_service_points'
down_revision: Union[str, Sequence[str], None] = '2c11_chat_memory'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'service_points',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('source_file', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('category_name', sa.String(length=100), nullable=True),
        sa.Column('category_slug', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('hotline_service', sa.String(length=50), nullable=True),
        sa.Column('booking_url', sa.String(length=500), nullable=True),
        sa.Column('dong_son', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('operating_hours', sa.String(length=255), nullable=True),
        sa.Column('services_offered', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('access_type', sa.String(length=50), nullable=False, server_default='Public'),
        sa.Column('is_car_compatible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.Column('crawled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('service_points', schema=None) as batch_op:
        batch_op.create_index('ix_service_points_source_file', ['source_file'], unique=False)
        batch_op.create_index('ix_service_points_source_id', ['source_id'], unique=False)
        batch_op.create_index('ix_service_points_category', ['category'], unique=False)
        batch_op.create_index('ix_service_points_category_slug', ['category_slug'], unique=False)
        batch_op.create_index('ix_service_points_name', ['name'], unique=False)
        batch_op.create_index('ix_service_points_latitude', ['latitude'], unique=False)
        batch_op.create_index('ix_service_points_longitude', ['longitude'], unique=False)
        batch_op.create_index('ix_service_points_status', ['status'], unique=False)
        batch_op.create_index('ix_service_points_access_type', ['access_type'], unique=False)
        batch_op.create_index('ix_service_points_is_visible', ['is_visible'], unique=False)
        batch_op.create_index('ix_service_points_cat_vis', ['category', 'is_visible'], unique=False)


def downgrade() -> None:
    op.drop_table('service_points')
