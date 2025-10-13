# File: src/services/scheduling_service.py

from typing import Dict, Any, Optional, List
from datetime import datetime, time
import json
import httpx
import asyncio
import logging
from sqlalchemy.orm import Session
from sqlalchemy_celery_beat.models import PeriodicTask, CrontabSchedule
from sqlalchemy import insert

from src.db import models as user_model
from src.core.config import settings

logger = logging.getLogger(__name__)


class SchedulingService:
    """
    Unified scheduling service that bridges Celery Beat (for recurring tasks) 
    and APScheduler (for one-time reminders and delayed automations).
    """
    
    def __init__(self):
        self.reminder_server_url = "http://reminder_server:8003"
        self.orchestrator_url = "http://orchestrator:8010"
        self.google_calendar_url = "http://google_calendar_server:8007"
        self.gmail_url = "http://gmail_server:8008"
    
    async def create_one_time_reminder(
        self, 
        time_str: str, 
        message: str, 
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Create a one-time reminder using APScheduler via reminder_server.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.reminder_server_url}/execute/set_reminder",
                    json={
                        "time_str": time_str,
                        "message": message,
                        "user_id": user_id
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Created one-time reminder for user {user_id}: {message}")
                    return {
                        "success": True,
                        "job_id": result.get("job_id"),
                        "scheduled_time": result.get("scheduled_time")
                    }
                else:
                    logger.error(f"Failed to create reminder: {response.text}")
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            logger.error(f"Error creating one-time reminder: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_recurring_schedule(
        self, 
        cron: str, 
        task: str, 
        kwargs: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Create a recurring schedule using Celery Beat (stored in database).
        """
        try:
            # Parse cron expression
            minute, hour, day_of_week, day_of_month, month_of_year = self._parse_cron(cron)
            
            # Find or create CrontabSchedule
            cron_schedule = db.query(CrontabSchedule).filter_by(
                minute=minute, hour=hour, day_of_week=day_of_week,
                day_of_month=day_of_month, month_of_year=month_of_year
            ).first()
            
            if not cron_schedule:
                cron_schedule = CrontabSchedule(
                    minute=minute, hour=hour, day_of_week=day_of_week,
                    day_of_month=day_of_month, month_of_year=month_of_year
                )
                db.add(cron_schedule)
                db.commit()
                db.refresh(cron_schedule)
            
            # Create periodic task
            task_name = f"{task} (User: {kwargs.get('user_id', 'system')})"
            
            stmt = insert(PeriodicTask.__table__).values(
                name=task_name,
                task=task,
                enabled=True,
                args=json.dumps([]),
                kwargs=json.dumps(kwargs),
                discriminator='crontab',
                schedule_id=cron_schedule.id
            )
            db.execute(stmt)
            db.commit()
            
            logger.info(f"Created recurring schedule: {task_name}")
            return {
                "success": True,
                "task_name": task_name,
                "cron_schedule": cron
            }
            
        except Exception as e:
            logger.error(f"Error creating recurring schedule: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    async def create_study_session(
        self, 
        schedule: user_model.StudySchedule, 
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Create a study session with both APScheduler reminders and Celery Beat execution.
        """
        try:
            # Parse time_str to get hour and minute
            hour, minute = self._parse_time_string(schedule.time_str)
            
            # Create cron expression based on schedule type
            if schedule.schedule_type == "daily":
                cron_expr = f"{minute} {hour} * * *"
            elif schedule.schedule_type == "weekly" and schedule.days_of_week:
                days_str = ",".join([str(d) for d in schedule.days_of_week])
                cron_expr = f"{minute} {hour} * * {days_str}"
            else:
                cron_expr = f"{minute} {hour} * * *"  # Default to daily
            
            # Create recurring task for study session execution
            recurring_result = await self.create_recurring_schedule(
                cron=cron_expr,
                task="src.tasks.study.send_study_reminder",
                kwargs={
                    "user_id": user_id,
                    "task_name": schedule.task_name,
                    "subject": schedule.subject,
                    "duration_minutes": schedule.duration_minutes
                },
                db=db
            )
            
            # Create APScheduler reminder (15 minutes before)
            reminder_time = f"{hour}:{minute-15 if minute >= 15 else hour-1}:{minute+45 if minute < 15 else minute-15}"
            reminder_result = await self.create_one_time_reminder(
                time_str=reminder_time,
                message=f"Study session starting in 15 minutes: {schedule.task_name}",
                user_id=user_id,
                db=db
            )
            
            return {
                "success": True,
                "recurring_task": recurring_result,
                "reminder": reminder_result
            }
            
        except Exception as e:
            logger.error(f"Error creating study session: {e}")
            return {"success": False, "error": str(e)}
    
    async def schedule_delayed_automation(
        self, 
        automation_type: str,
        action: str,
        parameters: Dict[str, Any],
        delay_str: str,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Schedule any automation for delayed execution using APScheduler.
        """
        try:
            # Create delayed automation record
            db_automation = user_model.DelayedAutomation(
                user_id=user_id,
                automation_type=automation_type,
                action=action,
                parameters=parameters,
                delay_str=delay_str,
                scheduled_time=datetime.now(),  # Will be updated by dateparser
                status="scheduled"
            )
            
            db.add(db_automation)
            db.commit()
            db.refresh(db_automation)
            
            # Schedule via APScheduler
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.reminder_server_url}/execute/set_reminder",
                    json={
                        "time_str": delay_str,
                        "message": json.dumps({
                            "type": "delayed_automation",
                            "automation_id": str(db_automation.uuid),
                            "automation_type": automation_type,
                            "action": action,
                            "parameters": parameters,
                            "user_id": user_id
                        }),
                        "user_id": user_id
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Update record with job ID
                    db_automation.apscheduler_job_id = result.get("job_id")
                    db.commit()
                    
                    logger.info(f"Scheduled delayed automation: {automation_type}.{action}")
                    return {
                        "success": True,
                        "automation_id": str(db_automation.uuid),
                        "job_id": result.get("job_id")
                    }
                else:
                    logger.error(f"Failed to schedule automation: {response.text}")
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            logger.error(f"Error scheduling delayed automation: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    async def sync_to_google_calendar(
        self, 
        timetable_entry: user_model.TimetableEntry,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Sync timetable entry to Google Calendar.
        """
        try:
            # Convert timetable entry to calendar event
            event_data = {
                "summary": f"{timetable_entry.subject}",
                "description": f"Class: {timetable_entry.subject}",
                "start": {
                    "dateTime": f"2024-01-01T{timetable_entry.start_time}:00",
                    "timeZone": "Asia/Kolkata"
                },
                "end": {
                    "dateTime": f"2024-01-01T{timetable_entry.end_time}:00",
                    "timeZone": "Asia/Kolkata"
                },
                "recurrence": [
                    f"RRULE:FREQ=WEEKLY;BYDAY={self._get_google_calendar_day(timetable_entry.day_of_week)}"
                ] if timetable_entry.recurring else None,
                "location": timetable_entry.room,
                "attendees": [
                    {"email": timetable_entry.teacher} if timetable_entry.teacher else None
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.google_calendar_url}/execute/create_event",
                    json={
                        "event_data": event_data,
                        "user_id": user_id
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Synced timetable entry to Google Calendar: {timetable_entry.subject}")
                    return {"success": True, "event_id": response.json().get("event_id")}
                else:
                    logger.error(f"Failed to sync to Google Calendar: {response.text}")
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            logger.error(f"Error syncing to Google Calendar: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_schedule_email(
        self, 
        user_email: str, 
        schedule_summary: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Send schedule summary email via Gmail.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gmail_url}/execute/send_email",
                    json={
                        "to": user_email,
                        "subject": "Weekly Schedule Summary",
                        "body": schedule_summary,
                        "user_id": user_id
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Sent schedule email to {user_email}")
                    return {"success": True, "message_id": response.json().get("message_id")}
                else:
                    logger.error(f"Failed to send schedule email: {response.text}")
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            logger.error(f"Error sending schedule email: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_cron(self, cron_schedule: str) -> tuple:
        """Parse cron expression into components."""
        try:
            minute, hour, day_of_week, day_of_month, month_of_year = cron_schedule.split()
            return minute, hour, day_of_week, day_of_month, month_of_year
        except ValueError:
            raise ValueError("Invalid cron_schedule format. Expected 5 fields: 'minute hour day_of_week day_of_month month_of_year'")
    
    def _parse_time_string(self, time_str: str) -> tuple:
        """Parse time string to get hour and minute."""
        import re
        
        # Try 24-hour format first
        time_match = re.match(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            return int(time_match.group(1)), int(time_match.group(2))
        
        # Try 12-hour format
        time_match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            period = time_match.group(3).upper()
            
            if period == "PM" and hour != 12:
                hour += 12
            elif period == "AM" and hour == 12:
                hour = 0
            
            return hour, minute
        
        raise ValueError("Invalid time format")
    
    def _get_google_calendar_day(self, day_of_week: int) -> str:
        """Convert day_of_week (0=Monday) to Google Calendar format (MO, TU, etc.)."""
        days = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        return days[day_of_week]
    
    async def get_user_schedule_summary(self, user_id: str, db: Session) -> str:
        """
        Generate a comprehensive schedule summary for a user.
        """
        try:
            # Get todos
            todos = db.query(user_model.Todo).filter(
                user_model.Todo.user_id == user_id,
                user_model.Todo.status.in_(["pending", "in_progress"])
            ).all()
            
            # Get timetable entries
            timetable = db.query(user_model.TimetableEntry).filter(
                user_model.TimetableEntry.user_id == user_id
            ).all()
            
            # Get study schedules
            study_schedules = db.query(user_model.StudySchedule).filter(
                user_model.StudySchedule.user_id == user_id,
                user_model.StudySchedule.enabled == True
            ).all()
            
            # Get delayed automations
            delayed_automations = db.query(user_model.DelayedAutomation).filter(
                user_model.DelayedAutomation.user_id == user_id,
                user_model.DelayedAutomation.status == "scheduled"
            ).all()
            
            # Generate summary
            summary = "📅 **Your Weekly Schedule Summary**\n\n"
            
            if todos:
                summary += "📝 **Pending Tasks:**\n"
                for todo in todos[:5]:  # Show top 5
                    due_info = f" (Due: {todo.due_date.strftime('%Y-%m-%d %H:%M')})" if todo.due_date else ""
                    summary += f"• {todo.title}{due_info}\n"
                summary += "\n"
            
            if timetable:
                summary += "🏫 **Class Schedule:**\n"
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                for entry in timetable:
                    day_name = days[entry.day_of_week]
                    summary += f"• {day_name} {entry.start_time}-{entry.end_time}: {entry.subject}"
                    if entry.room:
                        summary += f" ({entry.room})"
                    summary += "\n"
                summary += "\n"
            
            if study_schedules:
                summary += "📚 **Study Sessions:**\n"
                for schedule in study_schedules:
                    summary += f"• {schedule.task_name} - {schedule.subject} ({schedule.time_str})\n"
                summary += "\n"
            
            if delayed_automations:
                summary += "⏰ **Scheduled Automations:**\n"
                for automation in delayed_automations:
                    summary += f"• {automation.automation_type}.{automation.action} at {automation.scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating schedule summary: {e}")
            return "Error generating schedule summary"


# Global instance
scheduling_service = SchedulingService()
