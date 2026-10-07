"""Persist customer safety acknowledgements and chat ownership/idempotency."""
from alembic import op
import sqlalchemy as sa

revision = '2c10_chat_safety'
down_revision = '777b44e9e4d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cases', sa.Column('safety_status', sa.String(30), nullable=False, server_default='unconfirmed'))
    op.add_column('cases', sa.Column('safety_acknowledged_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cases', sa.Column('incident_version', sa.Integer(), nullable=False, server_default='1'))
    op.create_table('chat_sessions', sa.Column('id', sa.String(64), primary_key=True),
                    sa.Column('owner', sa.String(100), nullable=False), sa.Column('lease_token', sa.String(36)),
                    sa.Column('lease_until', sa.DateTime(timezone=True)))
    op.create_table('chat_request_records', sa.Column('id', sa.String(64), primary_key=True),
                    sa.Column('owner', sa.String(100), nullable=False), sa.Column('session_id', sa.String(64), nullable=False),
                    sa.Column('request_hash', sa.String(64), nullable=False), sa.Column('response', sa.JSON(), nullable=False))


def downgrade():
    op.drop_table('chat_request_records')
    op.drop_table('chat_sessions')
    with op.batch_alter_table('cases') as batch:
        batch.drop_column('incident_version')
        batch.drop_column('safety_acknowledged_at')
        batch.drop_column('safety_status')
