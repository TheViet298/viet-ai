"""create service_points table and ensure demo and vehicle metadata columns

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
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = set(insp.get_table_names())

    # 1. service_points table
    if 'service_points' not in tables:
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

    # 2. users columns: is_demo, full_name, phone, vehicle_model, mock_customer_id
    if 'users' in tables:
        users_cols = {c['name'] for c in insp.get_columns('users')}
        with op.batch_alter_table('users', schema=None) as batch_op:
            if 'full_name' not in users_cols:
                batch_op.add_column(sa.Column('full_name', sa.String(length=100), nullable=True))
            if 'phone' not in users_cols:
                batch_op.add_column(sa.Column('phone', sa.String(length=20), nullable=True))
            if 'vehicle_model' not in users_cols:
                batch_op.add_column(sa.Column('vehicle_model', sa.String(length=50), nullable=True))
            if 'mock_customer_id' not in users_cols:
                batch_op.add_column(sa.Column('mock_customer_id', sa.String(length=50), nullable=True))
            if 'is_demo' not in users_cols:
                batch_op.add_column(sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))

    # 3. cases columns: is_demo, vehicle_source, target_model, user_id, mock_customer_name, mock_customer_phone, safety_status, safety_acknowledged_at, incident_version
    if 'cases' in tables:
        cases_cols = {c['name'] for c in insp.get_columns('cases')}
        with op.batch_alter_table('cases', schema=None) as batch_op:
            if 'user_id' not in cases_cols:
                batch_op.add_column(sa.Column('user_id', sa.String(length=36), nullable=True))
            if 'mock_customer_name' not in cases_cols:
                batch_op.add_column(sa.Column('mock_customer_name', sa.String(length=100), nullable=True))
            if 'mock_customer_phone' not in cases_cols:
                batch_op.add_column(sa.Column('mock_customer_phone', sa.String(length=20), nullable=True))
            if 'safety_status' not in cases_cols:
                batch_op.add_column(sa.Column('safety_status', sa.String(length=30), server_default='unconfirmed', nullable=True))
            if 'safety_acknowledged_at' not in cases_cols:
                batch_op.add_column(sa.Column('safety_acknowledged_at', sa.DateTime(timezone=True), nullable=True))
            if 'incident_version' not in cases_cols:
                batch_op.add_column(sa.Column('incident_version', sa.Integer(), server_default='1', nullable=True))
            if 'is_demo' not in cases_cols:
                batch_op.add_column(sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))
            if 'vehicle_source' not in cases_cols:
                batch_op.add_column(sa.Column('vehicle_source', sa.String(length=30), nullable=True))
            if 'target_model' not in cases_cols:
                batch_op.add_column(sa.Column('target_model', sa.String(length=50), nullable=True))
            if 'owned_model' not in cases_cols:
                batch_op.add_column(sa.Column('owned_model', sa.String(length=50), nullable=True))

    # 4. chat_sessions columns: is_demo
    if 'chat_sessions' in tables:
        chat_cols = {c['name'] for c in insp.get_columns('chat_sessions')}
        with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
            if 'is_demo' not in chat_cols:
                batch_op.add_column(sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = set(insp.get_table_names())
    if 'service_points' in tables:
        op.drop_table('service_points')
