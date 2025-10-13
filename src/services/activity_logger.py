from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.db.models import ToolActivity
from src.db.session import get_sync_db_session
import uuid

class ActivityLogger:
    """Service for logging tool activities to the database"""
    
    @staticmethod
    async def log_activity(
        db: Session,
        user_id: uuid.UUID,
        activity_type: str,
        action: str,
        details: Optional[str] = None,
        status: str = "success"
    ) -> ToolActivity:
        """Log a tool activity to the database"""
        try:
            activity = ToolActivity(
                user_id=user_id,
                type=activity_type,
                action=action,
                details=details,
                status=status
            )
            
            db.add(activity)
            db.commit()
            db.refresh(activity)
            
            return activity
        except Exception as e:
            db.rollback()
            print(f"Error logging activity: {e}")
            raise e
    
    @staticmethod
    async def log_file_operation(
        db: Session,
        user_id: uuid.UUID,
        action: str,
        filename: str,
        status: str = "success",
        details: Optional[str] = None
    ) -> ToolActivity:
        """Log a file operation activity"""
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="file_operation",
            action=action,
            details=details or f"File: {filename}",
            status=status
        )
    
    @staticmethod
    async def log_web_search(
        db: Session,
        user_id: uuid.UUID,
        query: str,
        status: str = "success",
        results_count: Optional[int] = None
    ) -> ToolActivity:
        """Log a web search activity"""
        details = f"Query: {query}"
        if results_count is not None:
            details += f", Results: {results_count}"
        
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="web_search",
            action="search",
            details=details,
            status=status
        )
    
    @staticmethod
    async def log_email_operation(
        db: Session,
        user_id: uuid.UUID,
        action: str,
        recipient: Optional[str] = None,
        subject: Optional[str] = None,
        status: str = "success"
    ) -> ToolActivity:
        """Log an email operation activity"""
        details_parts = []
        if recipient:
            details_parts.append(f"To: {recipient}")
        if subject:
            details_parts.append(f"Subject: {subject}")
        
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="email",
            action=action,
            details="; ".join(details_parts) if details_parts else None,
            status=status
        )
    
    @staticmethod
    async def log_calendar_operation(
        db: Session,
        user_id: uuid.UUID,
        action: str,
        event_title: Optional[str] = None,
        event_date: Optional[str] = None,
        status: str = "success"
    ) -> ToolActivity:
        """Log a calendar operation activity"""
        details_parts = []
        if event_title:
            details_parts.append(f"Event: {event_title}")
        if event_date:
            details_parts.append(f"Date: {event_date}")
        
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="calendar",
            action=action,
            details="; ".join(details_parts) if details_parts else None,
            status=status
        )
    
    @staticmethod
    async def log_automation_operation(
        db: Session,
        user_id: uuid.UUID,
        action: str,
        automation_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ) -> ToolActivity:
        """Log an automation operation activity"""
        details = f"Type: {automation_type}"
        if parameters:
            details += f", Parameters: {str(parameters)}"
        
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="automation",
            action=action,
            details=details,
            status=status
        )
    
    @staticmethod
    async def log_shell_operation(
        db: Session,
        user_id: uuid.UUID,
        command: str,
        status: str = "success",
        output_length: Optional[int] = None
    ) -> ToolActivity:
        """Log a shell command execution activity"""
        details = f"Command: {command}"
        if output_length is not None:
            details += f", Output length: {output_length} chars"
        
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="shell",
            action="execute",
            details=details,
            status=status
        )
    
    @staticmethod
    async def log_google_drive_operation(
        db: Session,
        user_id: uuid.UUID,
        action: str,
        filename: Optional[str] = None,
        sync_type: Optional[str] = None,
        status: str = "success"
    ) -> ToolActivity:
        """Log a Google Drive operation activity"""
        details_parts = []
        if filename:
            details_parts.append(f"File: {filename}")
        if sync_type:
            details_parts.append(f"Sync: {sync_type}")
        
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="google_drive",
            action=action,
            details="; ".join(details_parts) if details_parts else None,
            status=status
        )
    
    @staticmethod
    async def log_folder_operation(
        db: Session,
        user_id: uuid.UUID,
        action: str,
        foldername: str,
        status: str = "success",
        details: Optional[str] = None
    ) -> ToolActivity:
        """Log a folder operation activity"""
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="folder_operation",
            action=action,
            details=details or f"Folder: {foldername}",
            status=status
        )
    
    @staticmethod
    async def log_reminder_operation(
        db: Session,
        user_id: uuid.UUID,
        action: str,
        message: str,
        time_str: str,
        status: str = "success",
        details: Optional[str] = None
    ) -> ToolActivity:
        """Log a reminder operation activity"""
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type="reminder",
            action=f"Reminder {action}",
            details=f"{message} at {time_str}",
            status=status
        )
