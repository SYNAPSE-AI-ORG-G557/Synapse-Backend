from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None  # Changed to str to handle empty strings
    priority: str = "medium"
    category: str = "general"

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None

class TimetableCreate(BaseModel):
    subject: str
    day_of_week: int
    start_time: str
    end_time: str
    room: Optional[str] = None
    teacher: Optional[str] = None
    recurring: bool = True

class StudyScheduleCreate(BaseModel):
    task_name: str
    subject: str
    schedule_type: str
    time_str: str
    duration_minutes: int = 60
    days_of_week: Optional[List[int]] = None
    enabled: bool = True

class DelayedAutomationCreate(BaseModel):
    automation_type: str
    action: str
    parameters: Dict[str, Any]
    delay_str: str
    conversation_id: Optional[str] = None
