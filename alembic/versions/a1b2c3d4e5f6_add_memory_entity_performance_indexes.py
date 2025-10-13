"""Add memory entity performance indexes

Revision ID: a1b2c3d4e5f6
Revises: f00aa8e36364
Create Date: 2025-01-11 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3fe4a7863d82'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for memory entities."""
    
    # Add individual indexes for frequently queried columns
    op.create_index('ix_memory_entities_user_id', 'memory_entities', ['user_id'])
    op.create_index('ix_memory_entities_conversation_id', 'memory_entities', ['conversation_id'])
    op.create_index('ix_memory_entities_access_count', 'memory_entities', ['access_count'])
    op.create_index('ix_memory_entities_importance_score', 'memory_entities', ['importance_score'])
    op.create_index('ix_memory_entities_created_at', 'memory_entities', ['created_at'])
    op.create_index('ix_memory_entities_expires_at', 'memory_entities', ['expires_at'])
    
    # Add composite indexes for common query patterns
    op.create_index('ix_memory_user_created', 'memory_entities', ['user_id', 'created_at'])
    op.create_index('ix_memory_user_importance', 'memory_entities', ['user_id', 'importance_score'])
    op.create_index('ix_memory_user_access', 'memory_entities', ['user_id', 'access_count'])
    op.create_index('ix_memory_conversation_created', 'memory_entities', ['conversation_id', 'created_at'])
    
    # Add vector index for embedding similarity search (if pgvector extension is available)
    try:
        op.execute('CREATE INDEX ix_memory_embedding_user ON memory_entities USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100) WHERE user_id IS NOT NULL')
    except Exception as e:
        # If pgvector extension is not available, skip the vector index
        print(f"Warning: Could not create vector index: {e}")


def downgrade():
    """Remove performance indexes for memory entities."""
    
    # Drop composite indexes
    op.drop_index('ix_memory_conversation_created', 'memory_entities')
    op.drop_index('ix_memory_user_access', 'memory_entities')
    op.drop_index('ix_memory_user_importance', 'memory_entities')
    op.drop_index('ix_memory_user_created', 'memory_entities')
    
    # Drop individual indexes
    op.drop_index('ix_memory_entities_expires_at', 'memory_entities')
    op.drop_index('ix_memory_entities_created_at', 'memory_entities')
    op.drop_index('ix_memory_entities_importance_score', 'memory_entities')
    op.drop_index('ix_memory_entities_access_count', 'memory_entities')
    op.drop_index('ix_memory_entities_conversation_id', 'memory_entities')
    op.drop_index('ix_memory_entities_user_id', 'memory_entities')
    
    # Drop vector index if it exists
    try:
        op.execute('DROP INDEX IF EXISTS ix_memory_embedding_user')
    except Exception:
        pass
