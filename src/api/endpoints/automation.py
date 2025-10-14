from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from src.core.dependencies import get_sync_db_session, get_current_user_sync
from src.db import models as user_model
from src.schemas.automation import TodoCreate, TodoUpdate, TimetableCreate, StudyScheduleCreate, DelayedAutomationCreate
router = APIRouter(prefix="/automation", tags=["Automation"])
log = structlog.get_logger(__name__)

@router.get("/todos")
def get_todos(
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_user_sync)
):
    """Get all todos for the current user"""
    try:
        todos = db.query(user_model.Todo).filter(
            user_model.Todo.user_id == current_user.uuid
        ).all()
        
        return {
            "status": "success",
            "todos": [
                {
                    "uuid": str(todo.uuid),
                    "title": todo.title,
                    "description": todo.description,
                    "due_date": todo.due_date.isoformat() if todo.due_date else None,
                    "priority": todo.priority,
                    "category": todo.category,
                    "status": todo.status,
                    "created_at": todo.created_at.isoformat(),
                    "updated_at": todo.updated_at.isoformat(),
                    "completed_at": todo.completed_at.isoformat() if todo.completed_at else None
                }
                for todo in todos
            ],
            "message": "Todos retrieved successfully"
        }
    except Exception as e:
        log.error(f"Failed to get todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/todos")
def create_todo(
    todo_data: TodoCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_user_sync)
):
    """Create a new todo"""
    try:
        # Parse due_date if provided and not empty
        parsed_due_date = None
        if todo_data.due_date and todo_data.due_date.strip():
            try:
                from datetime import datetime
                parsed_due_date = datetime.fromisoformat(todo_data.due_date.replace('Z', '+00:00'))
            except ValueError:
                log.warning(f"Invalid due_date format: {todo_data.due_date}")
                parsed_due_date = None
        
        todo = user_model.Todo(
            user_id=current_user.uuid,
            title=todo_data.title,
            description=todo_data.description,
            due_date=parsed_due_date,
            priority=todo_data.priority,
            category=todo_data.category
        )
        
        db.add(todo)
        db.commit()
        db.refresh(todo)
        
        return {
            "status": "success",
            "todo": {
                "uuid": str(todo.uuid),
                "title": todo.title,
                "description": todo.description,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "priority": todo.priority,
                "category": todo.category,
                "status": todo.status,
                "created_at": todo.created_at.isoformat(),
                "updated_at": todo.updated_at.isoformat()
            },
            "message": "Todo created successfully"
        }
    except Exception as e:
        log.error(f"Failed to create todo: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timetable")
def get_timetable(
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_user_sync)
):
    """Get timetable entries for the current user"""
    try:
        timetable = db.query(user_model.TimetableEntry).filter(
            user_model.TimetableEntry.user_id == current_user.uuid
        ).all()
        
        return {
            "status": "success",
            "timetable": [
                {
                    "uuid": str(entry.uuid),
                    "subject": entry.subject,
                    "day_of_week": entry.day_of_week,
                    "start_time": entry.start_time.strftime("%H:%M"),
                    "end_time": entry.end_time.strftime("%H:%M"),
                    "room": entry.room,
                    "teacher": entry.teacher,
                    "recurring": entry.recurring,
                    "created_at": entry.created_at.isoformat(),
                    "updated_at": entry.updated_at.isoformat()
                }
                for entry in timetable
            ],
            "message": "Timetable retrieved successfully"
        }
    except Exception as e:
        log.error(f"Failed to get timetable: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/timetable")
def create_timetable_entry(
    timetable_data: TimetableCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_user_sync)
):
    """Create a new timetable entry"""
    try:
        from datetime import time
        
        # Parse time strings
        start_time = time.fromisoformat(timetable_data.start_time)
        end_time = time.fromisoformat(timetable_data.end_time)
        
        entry = user_model.TimetableEntry(
            user_id=current_user.uuid,
            subject=timetable_data.subject,
            day_of_week=timetable_data.day_of_week,
            start_time=start_time,
            end_time=end_time,
            room=timetable_data.room,
            teacher=timetable_data.teacher,
            recurring=timetable_data.recurring
        )
        
        db.add(entry)
        db.commit()
        db.refresh(entry)
        
        return {
            "status": "success",
            "timetable": {
                "uuid": str(entry.uuid),
                "subject": entry.subject,
                "day_of_week": entry.day_of_week,
                "start_time": entry.start_time.strftime("%H:%M"),
                "end_time": entry.end_time.strftime("%H:%M"),
                "room": entry.room,
                "teacher": entry.teacher,
                "recurring": entry.recurring,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat()
            },
            "message": "Timetable entry created successfully"
        }
    except Exception as e:
        log.error(f"Failed to create timetable entry: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/study-schedules")
def get_study_schedules(
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_user_sync)
):
    """Get study schedules for the current user"""
    try:
        schedules = db.query(user_model.StudySchedule).filter(
            user_model.StudySchedule.user_id == current_user.uuid
        ).all()
        
        return {
            "status": "success",
            "schedules": [
                {
                    "uuid": str(schedule.uuid),
                    "task_name": schedule.task_name,
                    "subject": schedule.subject,
                    "schedule_type": schedule.schedule_type,
                    "time_str": schedule.time_str,
                    "duration_minutes": schedule.duration_minutes,
                    "days_of_week": schedule.days_of_week,
                    "enabled": schedule.enabled,
                    "created_at": schedule.created_at.isoformat(),
                    "updated_at": schedule.updated_at.isoformat()
                }
                for schedule in schedules
            ],
            "message": "Study schedules retrieved successfully"
        }
    except Exception as e:
        log.error(f"Failed to get study schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/study-schedule")
def create_study_schedule(
    schedule_data: StudyScheduleCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_user_sync)
):
    """Create a new study schedule"""
    try:
        schedule = user_model.StudySchedule(
            user_id=current_user.uuid,
            task_name=schedule_data.task_name,
            subject=schedule_data.subject,
            schedule_type=schedule_data.schedule_type,
            time_str=schedule_data.time_str,
            duration_minutes=schedule_data.duration_minutes,
            days_of_week=schedule_data.days_of_week,
            enabled=schedule_data.enabled
        )
        
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        
        return {
            "status": "success",
            "schedule": {
                "uuid": str(schedule.uuid),
                "task_name": schedule.task_name,
                "subject": schedule.subject,
                "schedule_type": schedule.schedule_type,
                "time_str": schedule.time_str,
                "duration_minutes": schedule.duration_minutes,
                "days_of_week": schedule.days_of_week,
                "enabled": schedule.enabled,
                "created_at": schedule.created_at.isoformat(),
                "updated_at": schedule.updated_at.isoformat()
            },
            "message": "Study schedule created successfully"
        }
    except Exception as e:
        log.error(f"Failed to create study schedule: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delayed-automation")
def create_delayed_automation(
    automation_data: DelayedAutomationCreate,
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_user_sync)
):
    """Create a delayed automation"""
    try:
        import dateparser

        # Parse delay string assuming user's local timezone (Asia/Kolkata) and convert to UTC for storage
        scheduled_time = dateparser.parse(
            automation_data.delay_str,
            settings={
                'PREFER_DATES_FROM': 'future',
                'TIMEZONE': 'Asia/Kolkata',
                'TO_TIMEZONE': 'UTC',
                'RETURN_AS_TIMEZONE_AWARE': True
            }
        )
        if not scheduled_time:
            raise ValueError("Could not parse delay string")
        
        automation = user_model.DelayedAutomation(
            user_id=current_user.uuid,
            conversation_id=automation_data.conversation_id,
            automation_type=automation_data.automation_type,
            action=automation_data.action,
            parameters=automation_data.parameters,
            delay_str=automation_data.delay_str,
            scheduled_time=scheduled_time
        )
        
        db.add(automation)
        db.commit()
        db.refresh(automation)
        
        return {
            "status": "success",
            "automation": {
                "uuid": str(automation.uuid),
                "automation_type": automation.automation_type,
                "action": automation.action,
                "parameters": automation.parameters,
                "delay_str": automation.delay_str,
                "scheduled_time": automation.scheduled_time.isoformat(),
                "status": automation.status,
                "created_at": automation.created_at.isoformat()
            },
            "message": "Delayed automation created successfully"
        }
    except Exception as e:
        log.error(f"Failed to create delayed automation: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
def get_delayed_automations(
    db: Session = Depends(get_sync_db_session),
    current_user: user_model.User = Depends(get_current_user_sync)
):
    """Get all delayed automations for the current user"""
    try:
        automations = db.query(user_model.DelayedAutomation).filter(
            user_model.DelayedAutomation.user_id == current_user.uuid
        ).all()
        
        return {
            "status": "success",
            "automations": [
                {
                    "uuid": str(automation.uuid),
                    "automation_type": automation.automation_type,
                    "action": automation.action,
                    "parameters": automation.parameters,
                    "delay_str": automation.delay_str,
                    "scheduled_time": automation.scheduled_time.isoformat(),
                    "status": automation.status,
                    "created_at": automation.created_at.isoformat(),
                    "executed_at": automation.executed_at.isoformat() if automation.executed_at else None
                }
                for automation in automations
            ],
            "message": "Delayed automations retrieved successfully"
        }
    except Exception as e:
        log.error(f"Failed to get delayed automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
