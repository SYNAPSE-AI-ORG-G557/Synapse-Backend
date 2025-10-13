"""add_schedule_tables

Revision ID: add_schedule_tables
Revises: f00aa8e36364
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_schedule_tables'
down_revision = 'f00aa8e36364'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create todos table
    op.create_table('todos',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('priority', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.uuid'], ),
        sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index('ix_todos_user_status', 'todos', ['user_id', 'status'], unique=False)
    op.create_index('ix_todos_user_due_date', 'todos', ['user_id', 'due_date'], unique=False)
    op.create_index('ix_todos_user_category', 'todos', ['user_id', 'category'], unique=False)
    op.create_index(op.f('ix_todos_user_id'), 'todos', ['user_id'], unique=False)
    op.create_index(op.f('ix_todos_due_date'), 'todos', ['due_date'], unique=False)
    op.create_index(op.f('ix_todos_status'), 'todos', ['status'], unique=False)

    # Create timetable_entries table
    op.create_table('timetable_entries',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('room', sa.String(), nullable=True),
        sa.Column('teacher', sa.String(), nullable=True),
        sa.Column('recurring', sa.Boolean(), nullable=False),
        sa.Column('periodic_task_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.uuid'], ),
        sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index('ix_timetable_user_day', 'timetable_entries', ['user_id', 'day_of_week'], unique=False)
    op.create_index('ix_timetable_user_subject', 'timetable_entries', ['user_id', 'subject'], unique=False)
    op.create_index(op.f('ix_timetable_entries_user_id'), 'timetable_entries', ['user_id'], unique=False)

    # Create study_schedules table
    op.create_table('study_schedules',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_name', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('schedule_type', sa.String(), nullable=False),
        sa.Column('time_str', sa.String(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('days_of_week', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('periodic_task_id', sa.Integer(), nullable=True),
        sa.Column('apscheduler_job_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.uuid'], ),
        sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index('ix_study_schedule_user_subject', 'study_schedules', ['user_id', 'subject'], unique=False)
    op.create_index('ix_study_schedule_user_type', 'study_schedules', ['user_id', 'schedule_type'], unique=False)
    op.create_index('ix_study_schedule_enabled', 'study_schedules', ['enabled'], unique=False)
    op.create_index(op.f('ix_study_schedules_user_id'), 'study_schedules', ['user_id'], unique=False)

    # Create delayed_automations table
    op.create_table('delayed_automations',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('automation_type', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('delay_str', sa.String(), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('apscheduler_job_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.uuid'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.uuid'], ),
        sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index('ix_delayed_automation_user_status', 'delayed_automations', ['user_id', 'status'], unique=False)
    op.create_index('ix_delayed_automation_scheduled_time', 'delayed_automations', ['scheduled_time'], unique=False)
    op.create_index('ix_delayed_automation_type', 'delayed_automations', ['automation_type'], unique=False)
    op.create_index(op.f('ix_delayed_automations_user_id'), 'delayed_automations', ['user_id'], unique=False)
    op.create_index(op.f('ix_delayed_automations_conversation_id'), 'delayed_automations', ['conversation_id'], unique=False)


def downgrade() -> None:
    # Drop delayed_automations table
    op.drop_index(op.f('ix_delayed_automations_conversation_id'), table_name='delayed_automations')
    op.drop_index(op.f('ix_delayed_automations_user_id'), table_name='delayed_automations')
    op.drop_index('ix_delayed_automation_type', table_name='delayed_automations')
    op.drop_index('ix_delayed_automation_scheduled_time', table_name='delayed_automations')
    op.drop_index('ix_delayed_automation_user_status', table_name='delayed_automations')
    op.drop_table('delayed_automations')

    # Drop study_schedules table
    op.drop_index(op.f('ix_study_schedules_user_id'), table_name='study_schedules')
    op.drop_index('ix_study_schedule_enabled', table_name='study_schedules')
    op.drop_index('ix_study_schedule_user_type', table_name='study_schedules')
    op.drop_index('ix_study_schedule_user_subject', table_name='study_schedules')
    op.drop_table('study_schedules')

    # Drop timetable_entries table
    op.drop_index(op.f('ix_timetable_entries_user_id'), table_name='timetable_entries')
    op.drop_index('ix_timetable_user_subject', table_name='timetable_entries')
    op.drop_index('ix_timetable_user_day', table_name='timetable_entries')
    op.drop_table('timetable_entries')

    # Drop todos table
    op.drop_index(op.f('ix_todos_status'), table_name='todos')
    op.drop_index(op.f('ix_todos_due_date'), table_name='todos')
    op.drop_index(op.f('ix_todos_user_id'), table_name='todos')
    op.drop_index('ix_todos_user_category', table_name='todos')
    op.drop_index('ix_todos_user_due_date', table_name='todos')
    op.drop_index('ix_todos_user_status', table_name='todos')
    op.drop_table('todos')
