"""add_tool_activities_table

Revision ID: 7dd188fa32a3
Revises: 7feb80f71314
Create Date: 2025-10-13 06:52:42.259745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dd188fa32a3'
down_revision: Union[str, Sequence[str], None] = '7feb80f71314'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create tool_activities table
    op.create_table(
        'tool_activities',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.uuid'], ),
        sa.PrimaryKeyConstraint('uuid')
    )
    
    # Create indexes
    op.create_index('ix_tool_activity_user_timestamp', 'tool_activities', ['user_id', 'timestamp'])
    op.create_index('ix_tool_activity_type', 'tool_activities', ['type'])
    op.create_index('ix_tool_activity_status', 'tool_activities', ['status'])
    op.create_index(op.f('ix_tool_activities_user_id'), 'tool_activities', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index(op.f('ix_tool_activities_user_id'), table_name='tool_activities')
    op.drop_index('ix_tool_activity_status', table_name='tool_activities')
    op.drop_index('ix_tool_activity_type', table_name='tool_activities')
    op.drop_index('ix_tool_activity_user_timestamp', table_name='tool_activities')
    
    # Drop table
    op.drop_table('tool_activities')
