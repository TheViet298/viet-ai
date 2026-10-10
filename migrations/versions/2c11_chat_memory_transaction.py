"""Keep application agent memory in the accepted chat transaction."""
import sqlalchemy as sa
from alembic import op

revision = '2c11_chat_memory'
down_revision = '2c10_chat_safety'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chat_sessions', sa.Column('memory_states', sa.JSON(), nullable=False, server_default='{}'))


def downgrade():
    with op.batch_alter_table('chat_sessions') as batch:
        batch.drop_column('memory_states')
