# File: src/db/models.py

# FIX: Rename uuid import to avoid namespace conflict
import uuid as uuid_lib
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from sqlalchemy import (
    String,
    DateTime,
    Text,
    Boolean,
    Integer,
    ForeignKey,
    Float,
    UUID as SA_UUID,
    func, 
    Date,
    Index,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Time
)
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from src.db.database import Base

# ------------------------- Core User and Session Models -------------------------

class User(Base):
    __tablename__ = "users"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    google_provider_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    google_access_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    google_refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    google_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_song_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    pfpb: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # profile picture
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- Relationships ---
    sessions: Mapped[List["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[List["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notification_preferences: Mapped[Optional["NotificationPreference"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memory_entities: Mapped[List["MemoryEntity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    api_calls: Mapped[List["ApiCall"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    processing_jobs: Mapped[List["ProcessingJob"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_messages: Mapped[List["ChatMessage"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    summaries: Mapped[List["ConversationSummary"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    todos: Mapped[List["Todo"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    timetable_entries: Mapped[List["TimetableEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    study_schedules: Mapped[List["StudySchedule"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    delayed_automations: Mapped[List["DelayedAutomation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tool_activities: Mapped[List["ToolActivity"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"
    
    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    user: Mapped["User"] = relationship(back_populates="sessions")


# ------------------------- Job and Task Processing Models -------------------------

class Task(Base):
    __tablename__ = "tasks"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False)

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", index=True, nullable=False)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    extra_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), 
                                                  onupdate=func.now(), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="tasks")
    task_results: Mapped[List["TaskResult"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskResult(Base):
    __tablename__ = "task_results"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    task_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("tasks.uuid"), nullable=False)

    result: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    task: Mapped["Task"] = relationship(back_populates="task_results")


# ------------------------- Notification Models -------------------------

class Notification(Base):
    __tablename__ = "notifications"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False)

    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), unique=True, nullable=False)

    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), 
                                                  onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="notification_preferences")


# ------------------------- Conversation and Memory Models -------------------------

class Conversation(Base):
    __tablename__ = "conversations"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False)
    title: Mapped[str] = mapped_column(String, default="New Chat", nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # ✨ --- NEW FIELDS FOR SHARING --- ✨
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    share_uuid: Mapped[Optional[uuid_lib.UUID]] = mapped_column(
        SA_UUID(as_uuid=True), unique=True, index=True, nullable=True
    )
    # ✨ ----------------------------- ✨

    # --- Relationships ---
    user: Mapped["User"] = relationship(back_populates="conversations")
    memory_entities: Mapped[List["MemoryEntity"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    summary: Mapped[Optional["ConversationSummary"]] = relationship(back_populates="conversation", uselist=False, cascade="all, delete-orphan")


class MemoryEntity(Base):
    __tablename__ = "memory_entities"
    
    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False, index=True)
    conversation_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(ForeignKey("conversations.uuid"), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768), nullable=True)
    extra_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    importance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    
    user: Mapped["User"] = relationship(back_populates="memory_entities")
    conversation: Mapped[Optional["Conversation"]] = relationship(back_populates="memory_entities")
    
    # Performance indexes for common query patterns
    __table_args__ = (
        # Composite index for user-based queries with time ordering
        Index("ix_memory_user_created", "user_id", "created_at"),
        # Composite index for user-based queries with importance
        Index("ix_memory_user_importance", "user_id", "importance_score"),
        # Composite index for user-based queries with access count
        Index("ix_memory_user_access", "user_id", "access_count"),
        # Index for vector similarity search optimization
        Index("ix_memory_embedding_user", "user_id", "embedding"),
        # Index for conversation-based queries
        Index("ix_memory_conversation_created", "conversation_id", "created_at"),
        # Index for expired memories cleanup
        Index("ix_memory_expires", "expires_at"),
    )

# ------------------------- Chat Message and Summary Models -------------------------

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    conversation_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("conversations.uuid"), nullable=False, index=True)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False, index=True)
    job_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(SA_UUID(as_uuid=True), nullable=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    user: Mapped["User"] = relationship(back_populates="chat_messages")
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    
    __table_args__ = (Index("ix_chat_messages_conversation_created_at", "conversation_id", "created_at"),)


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    conversation_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("conversations.uuid"), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    user: Mapped["User"] = relationship(back_populates="summaries")
    conversation: Mapped["Conversation"] = relationship(back_populates="summary", uselist=False)

# ------------------------- Vector and Processing Job Models -------------------------

class VectorEmbedding(Base):
    __tablename__ = "vector_embeddings"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    entity_id: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)

    vector: Mapped[List[float]] = mapped_column(Vector(1536), nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), 
                                                  onupdate=func.now(), nullable=False)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False, index=True)
    
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", index=True, nullable=False)
    input_data: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    result_data: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    user: Mapped["User"] = relationship(back_populates="processing_jobs")

# ------------------------- System and API Models -------------------------

class ApiCall(Base):
    __tablename__ = "api_calls"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(ForeignKey("users.uuid"), nullable=True)

    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    request_data: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    response_data: Mapped[Optional[dict[str, Any]]] = mapped_column(PG_JSON, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    token_cost: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[Optional["User"]] = relationship(back_populates="api_calls")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), 
                                                  onupdate=func.now(), nullable=False)
    updated_by: Mapped[Optional[uuid_lib.UUID]] = mapped_column(ForeignKey("users.uuid"), nullable=True)


# ------------------------- Schedule and Student Management Models -------------------------

class Todo(Base):
    __tablename__ = "todos"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False, index=True)
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String, default="medium", nullable=False)  # low, medium, high
    category: Mapped[str] = mapped_column(String, default="general", nullable=False)  # study, assignment, exam, project, personal
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False, index=True)  # pending, in_progress, completed
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        Index("ix_todos_user_status", "user_id", "status"),
        Index("ix_todos_user_due_date", "user_id", "due_date"),
        Index("ix_todos_user_category", "user_id", "category"),
    )


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False, index=True)
    
    subject: Mapped[str] = mapped_column(String, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time: Mapped[datetime] = mapped_column(Time, nullable=False)
    end_time: Mapped[datetime] = mapped_column(Time, nullable=False)
    room: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    teacher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    recurring: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Link to Celery Beat periodic task for notifications
    periodic_task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        Index("ix_timetable_user_day", "user_id", "day_of_week"),
        Index("ix_timetable_user_subject", "user_id", "subject"),
    )


class StudySchedule(Base):
    __tablename__ = "study_schedules"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False, index=True)
    
    task_name: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String, nullable=False)  # daily, weekly, exam_prep
    time_str: Mapped[str] = mapped_column(String, nullable=False)  # "18:00" or "6:00 PM"
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    days_of_week: Mapped[Optional[List[int]]] = mapped_column(PG_JSON, nullable=True)  # [1,3,5] for Mon,Wed,Fri
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Link to Celery Beat periodic task
    periodic_task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Link to APScheduler job for reminders
    apscheduler_job_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        Index("ix_study_schedule_user_subject", "user_id", "subject"),
        Index("ix_study_schedule_user_type", "user_id", "schedule_type"),
        Index("ix_study_schedule_enabled", "enabled"),
    )


class DelayedAutomation(Base):
    __tablename__ = "delayed_automations"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False, index=True)
    conversation_id: Mapped[Optional[uuid_lib.UUID]] = mapped_column(ForeignKey("conversations.uuid"), nullable=True, index=True)
    
    automation_type: Mapped[str] = mapped_column(String, nullable=False)  # browser, email, weather, search, file, etc.
    action: Mapped[str] = mapped_column(String, nullable=False)  # play, open, send, search, read, etc.
    parameters: Mapped[Dict[str, Any]] = mapped_column(PG_JSON, nullable=False)  # action-specific params
    delay_str: Mapped[str] = mapped_column(String, nullable=False)  # "5 minutes", "after 1 hour", "at 3 PM"
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String, default="scheduled", nullable=False)  # scheduled, executing, completed, failed
    apscheduler_job_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation")
    
    __table_args__ = (
        Index("ix_delayed_automation_user_status", "user_id", "status"),
        Index("ix_delayed_automation_scheduled_time", "scheduled_time"),
        Index("ix_delayed_automation_type", "automation_type"),
    )


# ------------------------- Tool Activity Tracking Model -------------------------

class ToolActivity(Base):
    __tablename__ = "tool_activities"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("users.uuid"), nullable=False, index=True)
    
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # file_operation, web_search, email, calendar, etc.
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # upload, download, delete, send, create, etc.
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Additional details about the activity
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)  # success, error, pending
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationship to user
    user: Mapped["User"] = relationship(back_populates="tool_activities")
    
    __table_args__ = (
        Index("ix_tool_activity_user_timestamp", "user_id", "timestamp"),
        Index("ix_tool_activity_type", "type"),
        Index("ix_tool_activity_status", "status"),
    )