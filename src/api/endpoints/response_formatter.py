"""
Response Formatter API Endpoints

Provides endpoints for formatting responses with rich markdown and HTML output.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import structlog

from src.core.dependencies import get_current_active_user
from src.services.response_formatter import ResponseFormatter

router = APIRouter(prefix="/response-formatter", tags=["Response Formatter"])
log = structlog.get_logger(__name__)

class FormatRequest(BaseModel):
    content: Any
    response_type: str = "general"
    metadata: Optional[Dict[str, Any]] = None

class FormatResponse(BaseModel):
    markdown: str
    html: str
    raw: str

@router.post("/format", response_model=FormatResponse)
async def format_response(
    request: FormatRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Format content with rich markdown and HTML output"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=request.content,
            response_type=request.response_type,
            metadata=request.metadata
        )
        
        log.info("Response formatted successfully", 
                user_id=current_user["uuid"], 
                response_type=request.response_type)
        
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format response", error=str(e), user_id=current_user["uuid"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format response: {str(e)}"
        )

@router.post("/format-internal", response_model=FormatResponse)
async def format_response_internal(request: FormatRequest):
    """Internal endpoint for formatting responses without authentication"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=request.content,
            response_type=request.response_type,
            metadata=request.metadata
        )
        
        log.info("Response formatted successfully (internal)", 
                response_type=request.response_type)
        
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format response (internal)", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format response: {str(e)}"
        )

@router.post("/format-automation-report", response_model=FormatResponse)
async def format_automation_report(
    content: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Format automation report with rich markdown"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=content,
            response_type="automation_report"
        )
        
        log.info("Automation report formatted successfully", user_id=current_user["uuid"])
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format automation report", error=str(e), user_id=current_user["uuid"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format automation report: {str(e)}"
        )

@router.post("/format-multi-step-result", response_model=FormatResponse)
async def format_multi_step_result(
    content: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Format multi-step automation result"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=content,
            response_type="multi_step_result"
        )
        
        log.info("Multi-step result formatted successfully", user_id=current_user["uuid"])
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format multi-step result", error=str(e), user_id=current_user["uuid"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format multi-step result: {str(e)}"
        )

@router.post("/format-file-operation", response_model=FormatResponse)
async def format_file_operation(
    content: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Format file operation report"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=content,
            response_type="file_operation"
        )
        
        log.info("File operation report formatted successfully", user_id=current_user["uuid"])
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format file operation report", error=str(e), user_id=current_user["uuid"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format file operation report: {str(e)}"
        )

@router.post("/format-google-drive", response_model=FormatResponse)
async def format_google_drive(
    content: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Format Google Drive operation report"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=content,
            response_type="google_drive"
        )
        
        log.info("Google Drive report formatted successfully", user_id=current_user["uuid"])
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format Google Drive report", error=str(e), user_id=current_user["uuid"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format Google Drive report: {str(e)}"
        )

@router.post("/format-google-sheets", response_model=FormatResponse)
async def format_google_sheets(
    content: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Format Google Sheets operation report"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=content,
            response_type="google_sheets"
        )
        
        log.info("Google Sheets report formatted successfully", user_id=current_user["uuid"])
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format Google Sheets report", error=str(e), user_id=current_user["uuid"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format Google Sheets report: {str(e)}"
        )

@router.post("/format-terminal", response_model=FormatResponse)
async def format_terminal(
    content: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Format terminal command report"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=content,
            response_type="terminal"
        )
        
        log.info("Terminal report formatted successfully", user_id=current_user["uuid"])
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format terminal report", error=str(e), user_id=current_user["uuid"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format terminal report: {str(e)}"
        )

@router.post("/format-schedule", response_model=FormatResponse)
async def format_schedule(
    content: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Format schedule operation report"""
    try:
        formatter = ResponseFormatter()
        result = formatter.format_response(
            content=content,
            response_type="schedule"
        )
        
        log.info("Schedule report formatted successfully", user_id=current_user["uuid"])
        return FormatResponse(**result)
        
    except Exception as e:
        log.error("Failed to format schedule report", error=str(e), user_id=current_user["uuid"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to format schedule report: {str(e)}"
        )

@router.get("/templates")
async def get_available_templates(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Get list of available response templates"""
    templates = [
        {
            "name": "general",
            "description": "General purpose response formatting",
            "example": "Basic markdown formatting for any content"
        },
        {
            "name": "automation_report",
            "description": "Automation workflow reports",
            "example": "Multi-step automation results with metrics"
        },
        {
            "name": "multi_step_result",
            "description": "Multi-step automation results",
            "example": "Detailed step-by-step automation execution"
        },
        {
            "name": "file_operation",
            "description": "File management operations",
            "example": "Upload, download, delete file operations"
        },
        {
            "name": "google_drive",
            "description": "Google Drive operations",
            "example": "Drive file upload, download, sharing reports"
        },
        {
            "name": "google_sheets",
            "description": "Google Sheets operations",
            "example": "Spreadsheet creation, data updates, sharing"
        },
        {
            "name": "terminal",
            "description": "Terminal command execution",
            "example": "Command output with syntax highlighting"
        },
        {
            "name": "schedule",
            "description": "Schedule and task management",
            "example": "Scheduled task creation and execution reports"
        }
    ]
    
    return {"templates": templates}

