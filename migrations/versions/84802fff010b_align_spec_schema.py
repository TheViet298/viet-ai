"""align_spec_schema

Revision ID: 84802fff010b
Revises: c9952f7d6ac7
Create Date: 2026-09-29 17:03:15.690014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '84802fff010b'
down_revision: Union[str, Sequence[str], None] = 'c9952f7d6ac7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Chuyển đổi từ schema nháp cũ sang 4 bảng chuẩn hóa theo data-model.md."""
    # 1. Xóa các bảng cũ (tickets, reviewer_feedback, case_briefs, staff_audit_logs, messages, cases)
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_cases")
    op.execute("DROP TABLE IF EXISTS tickets")
    op.execute("DROP TABLE IF EXISTS reviewer_feedback")
    op.execute("DROP TABLE IF EXISTS case_briefs")
    op.execute("DROP TABLE IF EXISTS staff_audit_logs")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS cases")

    # 2. Tạo bảng cases mới với khóa chính string (CASE-YYYYMMDD-XXX) và No-PII
    op.create_table(
        'cases',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('mock_customer_id', sa.String(length=50), nullable=True),
        sa.Column('mock_customer_name', sa.String(length=100), nullable=True),
        sa.Column('mock_customer_phone', sa.String(length=20), nullable=True),
        sa.Column('vehicle_code_mock', sa.String(length=50), nullable=True),
        sa.Column('vehicle_model', sa.String(length=50), nullable=True),
        sa.Column('intent', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('assigned_staff_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cases_session_id'), ['session_id'], unique=False)

    # 3. Tạo bảng messages mới với UUID và liên kết case_id String(32)
    op.create_table(
        'messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=32), nullable=True),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('sender_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sqlite.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_messages_case_id'), ['case_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_messages_session_id'), ['session_id'], unique=False)

    # 4. Tạo bảng case_briefs quan hệ 1-1 với cases
    op.create_table(
        'case_briefs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=32), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('captured_fields', sqlite.JSON(), nullable=False),
        sa.Column('suggested_action', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('is_edited_by_staff', sa.Boolean(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_id'),
    )

    # 5. Tạo bảng staff_audit_logs quan hệ 1-N với cases
    op.create_table(
        'staff_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=32), nullable=False),
        sa.Column('staff_id', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=30), nullable=False),
        sa.Column('previous_state', sqlite.JSON(), nullable=True),
        sa.Column('new_state', sqlite.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('staff_audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_staff_audit_logs_case_id'), ['case_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema về phiên bản cũ."""
    with op.batch_alter_table('staff_audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_staff_audit_logs_case_id'))
    op.drop_table('staff_audit_logs')
    op.drop_table('case_briefs')

    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_messages_session_id'))
        batch_op.drop_index(batch_op.f('ix_messages_case_id'))
    op.drop_table('messages')

    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cases_session_id'))
    op.drop_table('cases')

    # Khôi phục các bảng cũ
    op.create_table(
        'cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_channel', sa.String(length=30), nullable=False),
        sa.Column('customer_ref', sa.String(length=100), nullable=True),
        sa.Column('intent', sa.String(length=30), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('suggested_routing', sa.String(length=50), nullable=True),
        sa.Column('brief_data', sqlite.JSON(), nullable=True),
        sa.Column('ticket_status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('sender', sa.String(length=20), nullable=False),
        sa.Column('channel', sa.String(length=30), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'reviewer_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_name', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('edited_brief', sqlite.JSON(), nullable=True),
        sa.Column('final_routing', sa.String(length=50), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('assigned_department', sa.String(length=50), nullable=True),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.PrimaryKeyConstraint('id'),
    )
