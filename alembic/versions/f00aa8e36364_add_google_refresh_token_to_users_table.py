"""Add google_refresh_token to users table

Revision ID: f00aa8e36364
Revises: 44a5574ab04d
Create Date: 2025-10-09 12:57:29.496846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f00aa8e36364'
down_revision: Union[str, Sequence[str], None] = '44a5574ab04d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use idempotent SQL to avoid DuplicateColumnError if column already exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'google_refresh_token'
            ) THEN
                ALTER TABLE users ADD COLUMN google_refresh_token VARCHAR;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop column only if it exists to keep operation idempotent
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'google_refresh_token'
            ) THEN
                ALTER TABLE users DROP COLUMN google_refresh_token;
            END IF;
        END$$;
        """
    )