"""Add daily_song_subscribed to user model

Revision ID: 3fe4a7863d82
Revises: 9fe618a65ed3
Create Date: 2025-10-09 18:05:26.462129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fe4a7863d82'
down_revision: Union[str, Sequence[str], None] = '9fe618a65ed3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # This adds the new 'daily_song_subscribed' column to the 'users' table.
    # It's a Boolean type that cannot be null and defaults to 'false' for existing users.
    op.add_column(
        'users', 
        sa.Column(
            'daily_song_subscribed', 
            sa.Boolean(), 
            nullable=False, 
            server_default=sa.text('false')
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    # This removes the 'daily_song_subscribed' column from the 'users' table.
    op.drop_column('users', 'daily_song_subscribed')