# In: src/api/endpoints/automation.py

from fastapi import APIRouter, Depends, status, HTTPException, Path
from sqlalchemy.orm import Session
from sqlalchemy import insert
import json
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, time

from sqlalchemy_celery_beat.models import PeriodicTask, CrontabSchedule, ModelBase
from src.db.session import get_sync_db_session
from src.core.dependencies import get_current_active_user
from src.db import models as user_model
from pydantic import BaseModel

# Ensure SQLAlchemy-Celery tables use the correct schema
for table in ModelBase.metadata.tables.values():
    table.schema = "public"

router = APIRouter(prefix="/automation", tags=["automation"])


class WorkflowCreate(BaseModel):
    name: str
    task: str
    cron_schedule: str
    topic: str

# ... (rest of the Pydantic models and helper functions can remain the same) ...
class WorkflowOut(BaseModel):
    id: int
    name: str
    task: str
    cron_schedule: str
    kwargs: Dict[str, Any]
    enabled: bool


# Student-specific Pydantic models
class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None  # ISO format or natural language
    priority: str = "medium"  # low, medium, high
    category: str = "general"  # study, assignment, exam, project, personal


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None  # pending, in_progress, completed


class TodoOut(BaseModel):
    uuid: str
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: str
    category: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class TimetableCreate(BaseModel):
    subject: str
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # "09:00"
    end_time: str  # "10:30"
    room: Optional[str] = None
    teacher: Optional[str] = None
    recurring: bool = True


class TimetableOut(BaseModel):
    uuid: str
    subject: str
    day_of_week: int
    start_time: time
    end_time: time
    room: Optional[str]
    teacher: Optional[str]
    recurring: bool
    created_at: datetime
    updated_at: datetime


class StudyScheduleCreate(BaseModel):
    task_name: str
    subject: str
    schedule_type: str  # daily, weekly, exam_prep
    time_str: str  # "18:00" or "6:00 PM"
    duration_minutes: int = 60
    days_of_week: Optional[List[int]] = None
    enabled: bool = True


class StudyScheduleOut(BaseModel):
    uuid: str
    task_name: str
    subject: str
    schedule_type: str
    time_str: str
    duration_minutes: int
    days_of_week: Optional[List[int]]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class DelayedAutomationCreate(BaseModel):
    automation_type: str  # browser, email, weather, search, file, etc.
    action: str  # play, open, send, search, read, etc.
    parameters: Dict[str, Any]  # action-specific params
    delay_str: str  # "5 minutes", "after 1 hour", "at 3 PM", "in 30 seconds"
    conversation_id: Optional[str] = None


class DelayedAutomationOut(BaseModel):
    uuid: str
    automation_type: str
    action: str
    parameters: Dict[str, Any]
    delay_str: str
    scheduled_time: datetime
    status: str
    created_at: datetime
    executed_at: Optional[datetime]


def _parse_cron(cron_schedule: str):
    try:
        minute, hour, day_of_week, day_of_month, month_of_year = cron_schedule.split()
        return minute, hour, day_of_week, day_of_month, month_of_year
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid cron_schedule format. Expected 5 fields: 'minute hour day_of_week day_of_month month_of_year' (e.g. '*/5 * * * *')"
        )


def _task_belongs_to_user(periodic_task: PeriodicTask, user_uuid: str) -> bool:
    try:
        data = json.loads(periodic_task.kwargs or "{}")
        return data.get("user_id") == str(user_uuid)
    except Exception:
        return False


@router.post("/workflows", status_code=status.HTTP_201_CREATED)
def create_workflow(
    workflow: WorkflowCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """
    Creates a periodic task by bypassing the broken ORM and using a direct SQL insert.
    """
    minute, hour, day_of_week, day_of_month, month_of_year = _parse_cron(workflow.cron_schedule)

    try:
        # Step 1: Find or create the CrontabSchedule as before.
        cron = db.query(CrontabSchedule).filter_by(
            minute=minute, hour=hour, day_of_week=day_of_week,
            day_of_month=day_of_month, month_of_year=month_of_year
        ).first()

        if not cron:
            cron = CrontabSchedule(
                minute=minute, hour=hour, day_of_week=day_of_week,
                day_of_month=day_of_month, month_of_year=month_of_year
            )
            db.add(cron)
            db.commit()
            db.refresh(cron)

        task_name = f"{workflow.name} (User: {current_user.uuid})"
        existing = db.query(PeriodicTask).filter(PeriodicTask.name == task_name).first()
        if existing:
            raise HTTPException(status_code=400, detail="A workflow with this name already exists for this user.")

        # ✨ --- THE ULTIMATE FIX --- ✨
        # Bypass the buggy PeriodicTask object model and build a raw SQL INSERT statement.
        stmt = insert(PeriodicTask.__table__).values(
            name=task_name,
            task=workflow.task,
            enabled=True,
            args=json.dumps([]),
            kwargs=json.dumps({
                "user_id": str(current_user.uuid),
                "topic": workflow.topic
            }),
            discriminator='crontab',
            schedule_id=cron.id
        )
        db.execute(stmt)
        db.commit()

        return {"message": f"Workflow '{workflow.name}' scheduled successfully."}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {repr(e)}")


# The GET and DELETE endpoints can remain the same as they only read/delete data
# and do not run into the object creation bug.
@router.get("/workflows", response_model=List[WorkflowOut])
def list_workflows(
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    tasks = db.query(PeriodicTask).all()
    user_tasks = []
    for t in tasks:
        if _task_belongs_to_user(t, current_user.uuid):
            cron_str = ""
            if getattr(t, "crontab", None):
                c = t.crontab
                cron_str = f"{c.minute} {c.hour} {c.day_of_week} {c.day_of_month} {c.month_of_year}"
            user_tasks.append(WorkflowOut(
                id=t.id, name=t.name, task=t.task,
                cron_schedule=cron_str,
                kwargs=json.loads(t.kwargs or "{}"),
                enabled=t.enabled
            ))
    return user_tasks


@router.delete("/workflows/{task_id}", status_code=status.HTTP_200_OK)
def delete_workflow(
    task_id: int = Path(..., description="PeriodicTask id"),
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    task = db.query(PeriodicTask).filter(PeriodicTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    if not _task_belongs_to_user(task, current_user.uuid):
        raise HTTPException(status_code=403, detail="Not authorized to delete this workflow.")
    db.delete(task)
    db.commit()
    return {"message": "Workflow deleted."}


# ==================== STUDENT-SPECIFIC ENDPOINTS ====================

# Todo Management Endpoints
@router.post("/todos", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(
    todo: TodoCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """Create a new todo item with optional due date reminders"""
    import dateparser
    
    # Parse due_date if provided
    due_date = None
    if todo.due_date:
        try:
            due_date = dateparser.parse(todo.due_date, settings={'TIMEZONE': 'Asia/Kolkata'})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid due_date format")
    
    # Create todo in database
    db_todo = user_model.Todo(
        user_id=current_user.uuid,
        title=todo.title,
        description=todo.description,
        due_date=due_date,
        priority=todo.priority,
        category=todo.category,
        status="pending"
    )
    
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    
    # If due_date is set, create a reminder via APScheduler
    if due_date:
        try:
            # Create reminder via reminder server (sync approach)
            import requests
            response = requests.post(
                "http://reminder_server:8003/execute/set_reminder",
                json={
                    "time_str": todo.due_date,
                    "message": f"Reminder: {todo.title} is due!",
                    "user_id": str(current_user.uuid)
                },
                timeout=10
            )
            if response.status_code == 200:
                print(f"Reminder created for todo: {todo.title}")
        except Exception as e:
            # Log error but don't fail the todo creation
            print(f"Failed to create reminder: {e}")
    
    return TodoOut(
        uuid=str(db_todo.uuid),
        title=db_todo.title,
        description=db_todo.description,
        due_date=db_todo.due_date,
        priority=db_todo.priority,
        category=db_todo.category,
        status=db_todo.status,
        created_at=db_todo.created_at,
        updated_at=db_todo.updated_at,
        completed_at=db_todo.completed_at
    )


@router.get("/todos", response_model=List[TodoOut])
def list_todos(
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """List user's todos with optional filtering"""
    query = db.query(user_model.Todo).filter(user_model.Todo.user_id == current_user.uuid)
    
    if category:
        query = query.filter(user_model.Todo.category == category)
    if status:
        query = query.filter(user_model.Todo.status == status)
    
    todos = query.order_by(user_model.Todo.due_date.asc(), user_model.Todo.created_at.desc()).all()
    
    return [
        TodoOut(
            uuid=str(todo.uuid),
            title=todo.title,
            description=todo.description,
            due_date=todo.due_date,
            priority=todo.priority,
            category=todo.category,
            status=todo.status,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
            completed_at=todo.completed_at
        )
        for todo in todos
    ]


@router.put("/todos/{todo_uuid}", response_model=TodoOut)
def update_todo(
    todo_uuid: str,
    todo_update: TodoUpdate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """Update a todo item"""
    import uuid
    
    try:
        todo_id = uuid.UUID(todo_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid todo UUID")
    
    todo = db.query(user_model.Todo).filter(
        user_model.Todo.uuid == todo_id,
        user_model.Todo.user_id == current_user.uuid
    ).first()
    
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    # Update fields
    if todo_update.title is not None:
        todo.title = todo_update.title
    if todo_update.description is not None:
        todo.description = todo_update.description
    if todo_update.priority is not None:
        todo.priority = todo_update.priority
    if todo_update.category is not None:
        todo.category = todo_update.category
    if todo_update.status is not None:
        todo.status = todo_update.status
        if todo_update.status == "completed" and todo.completed_at is None:
            todo.completed_at = datetime.utcnow()
        elif todo_update.status != "completed":
            todo.completed_at = None
    
    if todo_update.due_date is not None:
        if todo_update.due_date:
            import dateparser
            try:
                todo.due_date = dateparser.parse(todo_update.due_date, settings={'TIMEZONE': 'Asia/Kolkata'})
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid due_date format")
        else:
            todo.due_date = None
    
    db.commit()
    db.refresh(todo)
    
    return TodoOut(
        uuid=str(todo.uuid),
        title=todo.title,
        description=todo.description,
        due_date=todo.due_date,
        priority=todo.priority,
        category=todo.category,
        status=todo.status,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        completed_at=todo.completed_at
    )


@router.delete("/todos/{todo_uuid}")
def delete_todo(
    todo_uuid: str,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """Delete a todo item"""
    import uuid
    
    try:
        todo_id = uuid.UUID(todo_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid todo UUID")
    
    todo = db.query(user_model.Todo).filter(
        user_model.Todo.uuid == todo_id,
        user_model.Todo.user_id == current_user.uuid
    ).first()
    
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    db.delete(todo)
    db.commit()
    
    return {"message": "Todo deleted successfully"}


# Timetable Management Endpoints
@router.post("/timetable", response_model=TimetableOut, status_code=status.HTTP_201_CREATED)
def create_timetable_entry(
    timetable: TimetableCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """Create a new timetable entry with class notifications"""
    try:
        start_time = datetime.strptime(timetable.start_time, "%H:%M").time()
        end_time = datetime.strptime(timetable.end_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
    
    # Create timetable entry
    db_entry = user_model.TimetableEntry(
        user_id=current_user.uuid,
        subject=timetable.subject,
        day_of_week=timetable.day_of_week,
        start_time=start_time,
        end_time=end_time,
        room=timetable.room,
        teacher=timetable.teacher,
        recurring=timetable.recurring
    )
    
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    # Create periodic task for class notifications (5 minutes before class)
    if timetable.recurring:
        try:
            # Calculate notification time (5 minutes before class)
            notification_time = datetime.strptime(timetable.start_time, "%H:%M")
            notification_minute = notification_time.minute - 5
            if notification_minute < 0:
                notification_time = notification_time.replace(hour=notification_time.hour - 1, minute=60 + notification_minute)
            else:
                notification_time = notification_time.replace(minute=notification_minute)
            
            # Create cron expression for weekly notification
            day_mapping = {0: "1", 1: "2", 2: "3", 3: "4", 4: "5", 5: "6", 6: "0"}  # Monday=1, Sunday=0
            cron_expr = f"{notification_time.minute} {notification_time.hour} * * {day_mapping[timetable.day_of_week]}"
            
            # Create periodic task
            minute, hour, day_of_week, day_of_month, month_of_year = _parse_cron(cron_expr)
            
            cron = db.query(CrontabSchedule).filter_by(
                minute=minute, hour=hour, day_of_week=day_of_week,
                day_of_month=day_of_month, month_of_year=month_of_year
            ).first()
            
            if not cron:
                cron = CrontabSchedule(
                    minute=minute, hour=hour, day_of_week=day_of_week,
                    day_of_month=day_of_month, month_of_year=month_of_year
                )
                db.add(cron)
                db.commit()
                db.refresh(cron)
            
            task_name = f"Class Reminder: {timetable.subject} (User: {current_user.uuid})"
            
            stmt = insert(PeriodicTask.__table__).values(
                name=task_name,
                task="src.tasks.notifications.send_class_reminder",
                enabled=True,
                args=json.dumps([]),
                kwargs=json.dumps({
                    "user_id": str(current_user.uuid),
                    "subject": timetable.subject,
                    "room": timetable.room,
                    "teacher": timetable.teacher
                }),
                discriminator='crontab',
                schedule_id=cron.id
            )
            db.execute(stmt)
            db.commit()
            
        except Exception as e:
            print(f"Failed to create class reminder: {e}")
    
    return TimetableOut(
        uuid=str(db_entry.uuid),
        subject=db_entry.subject,
        day_of_week=db_entry.day_of_week,
        start_time=db_entry.start_time,
        end_time=db_entry.end_time,
        room=db_entry.room,
        teacher=db_entry.teacher,
        recurring=db_entry.recurring,
        created_at=db_entry.created_at,
        updated_at=db_entry.updated_at
    )


@router.get("/timetable", response_model=List[TimetableOut])
def get_timetable(
    day_of_week: Optional[int] = None,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """Get user's timetable entries"""
    query = db.query(user_model.TimetableEntry).filter(user_model.TimetableEntry.user_id == current_user.uuid)
    
    if day_of_week is not None:
        query = query.filter(user_model.TimetableEntry.day_of_week == day_of_week)
    
    entries = query.order_by(user_model.TimetableEntry.day_of_week, user_model.TimetableEntry.start_time).all()
    
    return [
        TimetableOut(
            uuid=str(entry.uuid),
            subject=entry.subject,
            day_of_week=entry.day_of_week,
            start_time=entry.start_time,
            end_time=entry.end_time,
            room=entry.room,
            teacher=entry.teacher,
            recurring=entry.recurring,
            created_at=entry.created_at,
            updated_at=entry.updated_at
        )
        for entry in entries
    ]


# Study Schedule Management Endpoints
@router.post("/study-schedule", response_model=StudyScheduleOut, status_code=status.HTTP_201_CREATED)
def create_study_schedule(
    schedule: StudyScheduleCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """Create a study schedule with automatic reminders"""
    # Create study schedule
    db_schedule = user_model.StudySchedule(
        user_id=current_user.uuid,
        task_name=schedule.task_name,
        subject=schedule.subject,
        schedule_type=schedule.schedule_type,
        time_str=schedule.time_str,
        duration_minutes=schedule.duration_minutes,
        days_of_week=schedule.days_of_week,
        enabled=schedule.enabled
    )
    
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    
    # Create periodic task for study reminders
    if schedule.enabled:
        try:
            # Parse time_str to get hour and minute
            import re
            time_match = re.match(r'(\d{1,2}):(\d{2})', schedule.time_str)
            if not time_match:
                # Try 12-hour format
                time_match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', schedule.time_str, re.IGNORECASE)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    period = time_match.group(3).upper()
                    if period == "PM" and hour != 12:
                        hour += 12
                    elif period == "AM" and hour == 12:
                        hour = 0
                else:
                    raise ValueError("Invalid time format")
            else:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            
            # Create cron expression based on schedule type
            if schedule.schedule_type == "daily":
                cron_expr = f"{minute} {hour} * * *"
            elif schedule.schedule_type == "weekly" and schedule.days_of_week:
                # Convert days to cron format (1=Monday, 7=Sunday)
                days_str = ",".join([str(d) for d in schedule.days_of_week])
                cron_expr = f"{minute} {hour} * * {days_str}"
            else:
                cron_expr = f"{minute} {hour} * * *"  # Default to daily
            
            minute, hour, day_of_week, day_of_month, month_of_year = _parse_cron(cron_expr)
            
            cron = db.query(CrontabSchedule).filter_by(
                minute=minute, hour=hour, day_of_week=day_of_week,
                day_of_month=day_of_month, month_of_year=month_of_year
            ).first()
            
            if not cron:
                cron = CrontabSchedule(
                    minute=minute, hour=hour, day_of_week=day_of_week,
                    day_of_month=day_of_month, month_of_year=month_of_year
                )
                db.add(cron)
                db.commit()
                db.refresh(cron)
            
            task_name = f"Study Reminder: {schedule.task_name} (User: {current_user.uuid})"
            
            stmt = insert(PeriodicTask.__table__).values(
                name=task_name,
                task="src.tasks.notifications.send_study_reminder",
                enabled=True,
                args=json.dumps([]),
                kwargs=json.dumps({
                    "user_id": str(current_user.uuid),
                    "task_name": schedule.task_name,
                    "subject": schedule.subject,
                    "duration_minutes": schedule.duration_minutes
                }),
                discriminator='crontab',
                schedule_id=cron.id
            )
            db.execute(stmt)
            db.commit()
            
        except Exception as e:
            print(f"Failed to create study reminder: {e}")
    
    return StudyScheduleOut(
        uuid=str(db_schedule.uuid),
        task_name=db_schedule.task_name,
        subject=db_schedule.subject,
        schedule_type=db_schedule.schedule_type,
        time_str=db_schedule.time_str,
        duration_minutes=db_schedule.duration_minutes,
        days_of_week=db_schedule.days_of_week,
        enabled=db_schedule.enabled,
        created_at=db_schedule.created_at,
        updated_at=db_schedule.updated_at
    )


@router.get("/study-schedules", response_model=List[StudyScheduleOut])
def list_study_schedules(
    subject: Optional[str] = None,
    schedule_type: Optional[str] = None,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """List user's study schedules"""
    query = db.query(user_model.StudySchedule).filter(user_model.StudySchedule.user_id == current_user.uuid)
    
    if subject:
        query = query.filter(user_model.StudySchedule.subject == subject)
    if schedule_type:
        query = query.filter(user_model.StudySchedule.schedule_type == schedule_type)
    
    schedules = query.order_by(user_model.StudySchedule.subject, user_model.StudySchedule.time_str).all()
    
    return [
        StudyScheduleOut(
            uuid=str(schedule.uuid),
            task_name=schedule.task_name,
            subject=schedule.subject,
            schedule_type=schedule.schedule_type,
            time_str=schedule.time_str,
            duration_minutes=schedule.duration_minutes,
            days_of_week=schedule.days_of_week,
            enabled=schedule.enabled,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at
        )
        for schedule in schedules
    ]


# Delayed Automation Endpoints
@router.post("/delayed-automation", response_model=DelayedAutomationOut, status_code=status.HTTP_201_CREATED)
def create_delayed_automation(
    automation: DelayedAutomationCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """Schedule any automation task for delayed execution"""
    import dateparser
    import uuid
    
    # Parse delay_str to get scheduled time
    try:
        scheduled_time = dateparser.parse(automation.delay_str, settings={'TIMEZONE': 'Asia/Kolkata'})
        if not scheduled_time:
            raise ValueError("Could not parse delay string")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid delay format: {str(e)}")
    
    # Create delayed automation record
    conversation_id = None
    if automation.conversation_id:
        try:
            conversation_id = uuid.UUID(automation.conversation_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversation UUID")
    
    db_automation = user_model.DelayedAutomation(
        user_id=current_user.uuid,
        conversation_id=conversation_id,
        automation_type=automation.automation_type,
        action=automation.action,
        parameters=automation.parameters,
        delay_str=automation.delay_str,
        scheduled_time=scheduled_time,
        status="scheduled"
    )
    
    db.add(db_automation)
    db.commit()
    db.refresh(db_automation)
    
    # Schedule the automation via APScheduler (reminder_server)
    try:
        import httpx
        import asyncio
        
        async def schedule_automation():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://reminder_server:8003/execute/set_reminder",
                    json={
                        "time_str": automation.delay_str,
                        "message": json.dumps({
                            "type": "delayed_automation",
                            "automation_id": str(db_automation.uuid),
                            "automation_type": automation.automation_type,
                            "action": automation.action,
                            "parameters": automation.parameters,
                            "user_id": str(current_user.uuid)
                        }),
                        "user_id": str(current_user.uuid)
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    # Update the record with job ID if available
                    result = response.json()
                    if "job_id" in result:
                        db_automation.apscheduler_job_id = result["job_id"]
                        db.commit()
        
        # Schedule automation using sync approach
        try:
            import requests
            response = requests.post(
                f"{REMINDER_SERVER_URL}/execute/set_reminder",
                json={
                    "time_str": db_automation.delay_str,
                    "message": json.dumps({
                        "type": "delayed_automation",
                        "automation_type": db_automation.automation_type,
                        "action": db_automation.action,
                        "parameters": db_automation.parameters,
                        "user_id": str(current_user.uuid),
                        "automation_uuid": str(db_automation.uuid)
                    }),
                    "user_id": str(current_user.uuid)
                },
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if "job_id" in result:
                    db_automation.apscheduler_job_id = result["job_id"]
                    db.commit()
                print(f"Delayed automation scheduled: {db_automation.automation_type}")
        except Exception as e:
            print(f"Failed to schedule delayed automation: {e}")
        
    except Exception as e:
        print(f"Failed to schedule automation: {e}")
        # Don't fail the request, just log the error
    
    return DelayedAutomationOut(
        uuid=str(db_automation.uuid),
        automation_type=db_automation.automation_type,
        action=db_automation.action,
        parameters=db_automation.parameters,
        delay_str=db_automation.delay_str,
        scheduled_time=db_automation.scheduled_time,
        status=db_automation.status,
        created_at=db_automation.created_at,
        executed_at=db_automation.executed_at
    )


@router.get("/delayed-automations", response_model=List[DelayedAutomationOut])
def list_delayed_automations(
    status: Optional[str] = None,
    automation_type: Optional[str] = None,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user),
):
    """List user's delayed automations"""
    query = db.query(user_model.DelayedAutomation).filter(user_model.DelayedAutomation.user_id == current_user.uuid)
    
    if status:
        query = query.filter(user_model.DelayedAutomation.status == status)
    if automation_type:
        query = query.filter(user_model.DelayedAutomation.automation_type == automation_type)
    
    automations = query.order_by(user_model.DelayedAutomation.scheduled_time.desc()).all()
    
    return [
        DelayedAutomationOut(
            uuid=str(automation.uuid),
            automation_type=automation.automation_type,
            action=automation.action,
            parameters=automation.parameters,
            delay_str=automation.delay_str,
            scheduled_time=automation.scheduled_time,
            status=automation.status,
            created_at=automation.created_at,
            executed_at=automation.executed_at
        )
        for automation in automations
    ]


# Google Services Integration
class GoogleCalendarEventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start_datetime: str  # ISO format
    end_datetime: str    # ISO format
    location: Optional[str] = None
    attendees: Optional[List[str]] = None  # List of email addresses


class GmailNotificationCreate(BaseModel):
    to: str
    subject: str
    body: str
    schedule_time: Optional[str] = None  # For delayed emails


@router.post("/google-calendar/sync-timetable")
async def sync_timetable_to_google_calendar(
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """Sync all timetable entries to Google Calendar"""
    try:
        # Get all timetable entries for the user
        timetable_entries = db.query(user_model.TimetableEntry).filter(
            user_model.TimetableEntry.user_id == current_user.uuid
        ).all()
        
        if not timetable_entries:
            return {"message": "No timetable entries found to sync"}
        
        synced_events = []
        
        for entry in timetable_entries:
            # Create Google Calendar event for each timetable entry
            event_data = {
                "summary": f"{entry.subject} - {entry.teacher or 'Class'}",
                "description": f"Room: {entry.room or 'TBD'}\nTeacher: {entry.teacher or 'TBD'}",
                "start_datetime": f"2024-01-{entry.day_of_week + 1}T{entry.start_time}:00",
                "end_datetime": f"2024-01-{entry.day_of_week + 1}T{entry.end_time}:00",
                "location": entry.room,
                "recurring": entry.recurring
            }
            
            # Call Google Calendar server
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://google_calendar_server:8007/execute/create_event",
                    json=event_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    synced_events.append({
                        "subject": entry.subject,
                        "event_id": response.json().get("event_id"),
                        "status": "synced"
                    })
                else:
                    synced_events.append({
                        "subject": entry.subject,
                        "status": "failed",
                        "error": response.text
                    })
        
        return {
            "message": f"Synced {len(synced_events)} timetable entries to Google Calendar",
            "events": synced_events
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync timetable: {str(e)}")


@router.post("/google-calendar/create-event")
async def create_google_calendar_event(
    event: GoogleCalendarEventCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """Create a new event in Google Calendar"""
    try:
        # Call Google Calendar server
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://google_calendar_server:8007/execute/create_event",
                json=event.dict(),
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "message": "Event created successfully in Google Calendar",
                    "event": response.json()
                }
            else:
                raise HTTPException(status_code=400, detail=f"Failed to create event: {response.text}")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Google Calendar event: {str(e)}")


@router.get("/google-calendar/events")
async def get_google_calendar_events(
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """Get upcoming events from Google Calendar"""
    try:
        # Call Google Calendar server
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://google_calendar_server:8007/execute/get_events",
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "message": "Events retrieved successfully",
                    "events": response.json()
                }
            else:
                raise HTTPException(status_code=400, detail=f"Failed to get events: {response.text}")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Google Calendar events: {str(e)}")


@router.post("/gmail/send-notification")
async def send_gmail_notification(
    notification: GmailNotificationCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """Send email notification via Gmail"""
    try:
        email_data = {
            "to": notification.to,
            "subject": notification.subject,
            "body": notification.body,
            "user_auth_token": current_user.google_access_token or ""
        }
        
        # Call Gmail server
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://gmail_server:8008/execute/send_email",
                json=email_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "message": "Email sent successfully",
                    "email": response.json()
                }
            else:
                raise HTTPException(status_code=400, detail=f"Failed to send email: {response.text}")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send Gmail notification: {str(e)}")


@router.post("/gmail/schedule-notification")
async def schedule_gmail_notification(
    notification: GmailNotificationCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """Schedule a delayed email notification"""
    try:
        if not notification.schedule_time:
            raise HTTPException(status_code=400, detail="schedule_time is required for delayed emails")
        
        # Create delayed automation for email
        delayed_automation = user_model.DelayedAutomation(
            user_id=current_user.uuid,
            automation_type="email",
            action="send",
            parameters={
                "to": notification.to,
                "subject": notification.subject,
                "body": notification.body,
                "user_auth_token": current_user.google_access_token or ""
            },
            delay_str=notification.schedule_time,
            scheduled_time=datetime.now()  # Will be updated by the scheduling service
        )
        
        db.add(delayed_automation)
        db.commit()
        db.refresh(delayed_automation)
        
        # Schedule via reminder server
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://reminder_server:8003/execute/set_reminder",
                json={
                    "time_str": notification.schedule_time,
                    "message": json.dumps({
                        "type": "delayed_automation",
                        "automation_type": "email",
                        "action": "send",
                        "parameters": {
                            "to": notification.to,
                            "subject": notification.subject,
                            "body": notification.body,
                            "user_auth_token": current_user.google_access_token or ""
                        },
                        "user_id": str(current_user.uuid)
                    }),
                    "user_id": str(current_user.uuid)
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "message": "Email notification scheduled successfully",
                    "automation_id": str(delayed_automation.uuid),
                    "scheduled_time": notification.schedule_time
                }
            else:
                raise HTTPException(status_code=400, detail=f"Failed to schedule email: {response.text}")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule Gmail notification: {str(e)}")


@router.post("/integrate/sync-all")
async def sync_all_to_google_services(
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """Sync all schedule data to Google services"""
    try:
        results = {
            "calendar_sync": None,
            "email_summary": None,
            "errors": []
        }
        
        # 1. Sync timetable to Google Calendar
        try:
            calendar_result = await sync_timetable_to_google_calendar(db, current_user)
            results["calendar_sync"] = calendar_result
        except Exception as e:
            results["errors"].append(f"Calendar sync failed: {str(e)}")
        
        # 2. Send weekly summary email
        try:
            # Get todos and study schedules for summary
            todos = db.query(user_model.Todo).filter(
                user_model.Todo.user_id == current_user.uuid,
                user_model.Todo.status == "pending"
            ).all()
            
            study_schedules = db.query(user_model.StudySchedule).filter(
                user_model.StudySchedule.user_id == current_user.uuid,
                user_model.StudySchedule.enabled == True
            ).all()
            
            # Create summary email
            summary_body = f"""
            <h2>Weekly Schedule Summary</h2>
            <h3>Pending Tasks ({len(todos)})</h3>
            <ul>
            {''.join([f'<li>{todo.title} - Due: {todo.due_date or "No due date"}</li>' for todo in todos])}
            </ul>
            
            <h3>Active Study Schedules ({len(study_schedules)})</h3>
            <ul>
            {''.join([f'<li>{schedule.task_name} - {schedule.subject} at {schedule.time_str}</li>' for schedule in study_schedules])}
            </ul>
            
            <p>Keep up the great work with your studies!</p>
            """
            
            email_data = {
                "to": current_user.email,
                "subject": "Weekly Schedule Summary - Synapse AI",
                "body": summary_body,
                "user_auth_token": current_user.google_access_token or ""
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://gmail_server:8008/execute/send_email",
                    json=email_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    results["email_summary"] = {
                        "message": "Weekly summary email sent successfully",
                        "email": response.json()
                    }
                else:
                    results["errors"].append(f"Email summary failed: {response.text}")
                    
        except Exception as e:
            results["errors"].append(f"Email summary failed: {str(e)}")
        
        return {
            "message": "Google services integration completed",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync with Google services: {str(e)}")