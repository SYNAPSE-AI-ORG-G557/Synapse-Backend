# In Synapse-Backend/alembic/env.py

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from alembic.operations import ops
from alembic.autogenerate import api

# --- CUSTOM IMPORTS START ---
from src.db.models import Base
from sqlalchemy_celery_beat.models import ModelBase
# --- CUSTOM IMPORTS END ---


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- METADATA CONFIGURATION ---
ModelBase.metadata.schema = "public"
target_metadata = Base.metadata
for table in ModelBase.metadata.tables.values():
    table.tometadata(target_metadata)
# --- METADATA CONFIGURATION END ---


# ✨ --- THE DEFINITIVE FIX v3 --- ✨
# This version uses the correct decorator syntax but adds a guard clause
# to prevent the AssertionError caused by env.py being loaded multiple times.
# We check the internal registry to see if a renderer for this operation
# has already been registered.

# The key for the registry is a tuple: (operation_class, qualifier)
create_table_key = (ops.CreateTableOp, "default")
drop_table_key = (ops.DropTableOp, "default")

if create_table_key not in api.render.renderers._registry:
    @api.render.renderers.dispatch_for(ops.CreateTableOp)
    def render_celery_schema_less(renderer, op):
        """A hook to remove the schema from Celery's CreateTable operations."""
        if op.table_name.startswith("celery_"):
            op.schema = None  # Force schema to be None (i.e., public)
        return renderer.dispatch(op)

if drop_table_key not in api.render.renderers._registry:
    @api.render.renderers.dispatch_for(ops.DropTableOp)
    def render_celery_drop_schema_less(renderer, op):
        """A hook to remove the schema from Celery's DropTable operations."""
        if op.table_name.startswith("celery_"):
            op.schema = None # Force schema to be None for downgrade operations
        return renderer.dispatch(op)
# ✨ --- END OF FIX --- ✨


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())