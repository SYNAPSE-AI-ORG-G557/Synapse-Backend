from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import httpx
import os
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from src.core.config import settings
from src.core.dependencies import get_current_user_sync
from src.db.session import get_sync_db_session

router = APIRouter()

# File Access Server Configuration
FILE_ACCESS_SERVER_URL = "http://file_access_server:8002"
REMINDER_SERVER_URL = "http://reminder_server:8003"

@router.get("/files")
async def get_files(
    folder_path: str = "",
    search_query: str = "",
    file_type: str = "",
    sort_by: str = "name",
    sort_order: str = "asc",
    user = Depends(get_current_user_sync)
):
    """Get all files from the file access server with advanced filtering and sorting"""
    try:
        async with httpx.AsyncClient() as client:
            # List files in the safe directory
            response = await client.get(f"{FILE_ACCESS_SERVER_URL}/list_files")
            if response.status_code == 200:
                data = response.json()
                # Transform the data to match frontend expectations
                files = []
                for file_info in data.get("files", []):
                    # Convert Unix timestamp to ISO format
                    created_time = datetime.fromtimestamp(file_info['created']).isoformat() + 'Z'
                    
                    # Apply search filter
                    if search_query and search_query.lower() not in file_info["name"].lower():
                        continue
                    
                    # Apply file type filter
                    if file_type and file_info["type"] != file_type:
                        continue
                    
                    # Apply folder path filter
                    if folder_path and not file_info["name"].startswith(folder_path):
                        continue
                    
                    files.append({
                        "id": hash(file_info["name"]),  # Generate a simple ID
                        "name": file_info["name"],
                        "size": f"{file_info['size']} bytes",
                        "size_bytes": file_info['size'],
                        "created": created_time,
                        "type": file_info["type"],
                        "is_folder": file_info.get("is_folder", False),
                        "content": ""  # Will be loaded separately when needed
                    })
                
                # Apply sorting
                if sort_by == "name":
                    files.sort(key=lambda x: x["name"].lower(), reverse=(sort_order == "desc"))
                elif sort_by == "size":
                    files.sort(key=lambda x: x["size_bytes"], reverse=(sort_order == "desc"))
                elif sort_by == "created":
                    files.sort(key=lambda x: x["created"], reverse=(sort_order == "desc"))
                
                return {
                    "files": files,
                    "total_count": len(files),
                    "folder_path": folder_path,
                    "search_query": search_query
                }
            else:
                return {"files": [], "total_count": 0}
    except Exception as e:
        print(f"Error fetching files: {e}")
        return {"files": [], "total_count": 0}

@router.get("/files/{filename}")
async def get_file_content(filename: str):
    """Get content of a specific file"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/read_file",
                json={"path": filename}
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Delete a file or folder"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/delete_file",
                json={"path": filename}
            )
            if response.status_code == 200:
                # Log the activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="delete",
                    filename=filename,
                    status="success"
                )
                return {"message": "File deleted successfully"}
            else:
                # Log failed activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="delete",
                    filename=filename,
                    status="error",
                    details=f"Failed with status {response.status_code}"
                )
                raise HTTPException(status_code=400, detail="Failed to delete file")
    except Exception as e:
        # Log error activity
        try:
            from src.services.activity_logger import ActivityLogger
            await ActivityLogger.log_file_operation(
                db=db,
                user_id=user.uuid,
                action="delete",
                filename=filename,
                status="error",
                details=str(e)
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@router.get("/files/{filename}/read")
async def read_file(filename: str):
    """Read file content for viewing"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/read_file",
                json={"path": filename}
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Delete a file or folder"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/delete_file",
                json={"path": filename}
            )
            if response.status_code == 200:
                # Log the activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="delete",
                    filename=filename,
                    status="success"
                )
                return {"message": "File deleted successfully"}
            else:
                # Log failed activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="delete",
                    filename=filename,
                    status="error",
                    details=f"Failed with status {response.status_code}"
                )
                raise HTTPException(status_code=400, detail="Failed to delete file")
    except Exception as e:
        # Log error activity
        try:
            from src.services.activity_logger import ActivityLogger
            await ActivityLogger.log_file_operation(
                db=db,
                user_id=user.uuid,
                action="delete",
                filename=filename,
                status="error",
                details=str(e)
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@router.get("/files/{filename}/download")
async def download_file(filename: str):
    """Download file content as binary"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/read_file",
                json={"path": filename}
            )
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                # Return as downloadable response
                from fastapi.responses import Response
                return Response(
                    content=content.encode('utf-8'),
                    media_type='application/octet-stream',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"'
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

@router.post("/files")
async def create_file(
    request: Request,
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Create a new file or folder"""
    try:
        # Parse JSON body
        body = await request.json()
        filename = body.get("name")
        content = body.get("content", "")
        is_folder = body.get("is_folder", False)
        
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        async with httpx.AsyncClient() as client:
            if is_folder:
                # Create folder by creating a file with folder marker
                response = await client.post(
                    f"{FILE_ACCESS_SERVER_URL}/execute/write_file",
                    json={"path": f"{filename}/.folder", "content": ""}
                )
            else:
                # Create regular file
                response = await client.post(
                    f"{FILE_ACCESS_SERVER_URL}/execute/write_file",
                    json={"path": filename, "content": content}
                )
            
            if response.status_code == 200:
                # Log the activity
                from src.services.activity_logger import ActivityLogger
                if is_folder:
                    await ActivityLogger.log_folder_operation(
                        db=db,
                        user_id=user.uuid,
                        action="create",
                        foldername=filename,
                        status="success"
                    )
                else:
                    await ActivityLogger.log_file_operation(
                        db=db,
                        user_id=user.uuid,
                        action="create",
                        filename=filename,
                        status="success"
                    )
                return {"message": "File created successfully", "filename": filename}
            else:
                # Log failed activity
                from src.services.activity_logger import ActivityLogger
                if is_folder:
                    await ActivityLogger.log_folder_operation(
                        db=db,
                        user_id=user.uuid,
                        action="create",
                        foldername=filename,
                        status="error",
                        details=f"Failed with status {response.status_code}"
                    )
                else:
                    await ActivityLogger.log_file_operation(
                        db=db,
                        user_id=user.uuid,
                        action="create",
                        filename=filename,
                        status="error",
                        details=f"Failed with status {response.status_code}"
                    )
                raise HTTPException(status_code=400, detail="Failed to create file")
    except Exception as e:
        # Log error activity
        try:
            from src.services.activity_logger import ActivityLogger
            if is_folder:
                await ActivityLogger.log_folder_operation(
                    db=db,
                    user_id=user.uuid,
                    action="create",
                    foldername=filename,
                    status="error",
                    details=str(e)
                )
            else:
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="create",
                    filename=filename,
                    status="error",
                    details=str(e)
                )
        except:
            pass  # Don't fail the main operation if logging fails
        raise HTTPException(status_code=500, detail=f"Error creating file: {str(e)}")

@router.delete("/files/{filename}")
async def delete_file(filename: str):
    """Delete a file"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{FILE_ACCESS_SERVER_URL}/execute/delete_file/{filename}")
            if response.status_code == 200:
                return {"message": "File deleted successfully", "filename": filename}
            else:
                raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@router.get("/reminders")
async def get_reminders():
    """Get all active reminders from the reminder server"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{REMINDER_SERVER_URL}/list_reminders")
            if response.status_code == 200:
                data = response.json()
                # Transform the data to match frontend expectations
                reminders = []
                for reminder_info in data.get("reminders", []):
                    reminders.append({
                        "id": hash(reminder_info["id"]),  # Generate a simple ID
                        "message": reminder_info["message"],
                        "time": reminder_info["scheduled_time"],
                        "status": reminder_info["status"],
                        "created": reminder_info["scheduled_time"]  # Use scheduled time as created time
                    })
                return {"reminders": reminders}
            else:
                return {"reminders": []}
    except Exception as e:
        print(f"Error fetching reminders: {e}")
        return {"reminders": []}

@router.post("/reminders")
async def create_reminder(
    request: Request,
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Create a new reminder"""
    try:
        # Parse JSON body
        body = await request.json()
        message = body.get("message")
        time_str = body.get("time_str")
        
        if not message or not time_str:
            raise HTTPException(status_code=400, detail="Message and time_str are required")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{REMINDER_SERVER_URL}/execute/set_reminder",
                json={
                    "message": message,
                    "time_str": time_str,
                    "user_id": str(user.uuid)
                }
            )
            if response.status_code == 200:
                # Log the activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_reminder_operation(
                    db=db,
                    user_id=user.uuid,
                    action="create",
                    message=message,
                    time_str=time_str,
                    status="success"
                )
                return {"message": "Reminder created successfully", "reminder": response.json()}
            else:
                # Log error activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_reminder_operation(
                    db=db,
                    user_id=user.uuid,
                    action="create",
                    message=message,
                    time_str=time_str,
                    status="error",
                    details=f"Failed with status {response.status_code}"
                )
                raise HTTPException(status_code=400, detail="Failed to create reminder")
    except Exception as e:
        # Log error activity
        try:
            from src.services.activity_logger import ActivityLogger
            await ActivityLogger.log_reminder_operation(
                db=db,
                user_id=user.uuid,
                action="create",
                message=message,
                time_str=time_str,
                status="error",
                details=str(e)
            )
        except:
            pass  # Don't fail the main operation if logging fails
        raise HTTPException(status_code=500, detail=f"Error creating reminder: {str(e)}")

@router.get("/activities")
async def get_tool_activities(
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Get user's tool activities from database"""
    try:
        from src.db.models import ToolActivity
        
        activities = db.query(ToolActivity)\
            .filter(ToolActivity.user_id == user.uuid)\
            .order_by(ToolActivity.timestamp.desc())\
            .limit(50)\
            .all()
        
        return {
            "activities": [
                {
                    "id": str(activity.uuid),
                    "type": activity.type,
                    "action": activity.action,
                    "details": activity.details,
                    "timestamp": activity.timestamp.isoformat(),
                    "status": activity.status
                }
                for activity in activities
            ]
        }
    except Exception as e:
        print(f"Error fetching activities: {e}")
        # Return mock data as fallback
        return {
            "activities": [
                {
                    "id": 1,
                    "type": "file_operation",
                    "action": "File Created",
                    "details": "test.txt",
                    "timestamp": "2025-10-11T04:58:22Z",
                    "status": "success"
                },
                {
                    "id": 2,
                    "type": "web_search",
                    "action": "Web Search",
                    "details": "Latest news on MERN stack",
                    "timestamp": "2025-10-11T04:56:37Z",
                    "status": "success"
                },
                {
                    "id": 3,
                    "type": "reminder",
                    "action": "Reminder Set",
                    "details": "Check my email in 2 minutes",
                    "timestamp": "2025-10-11T04:55:00Z",
                    "status": "success"
                }
            ]
        }

@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder_path: str = Form(""),
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Upload a file with drag & drop support"""
    try:
        # Validate file size (max 10MB)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File size too large. Maximum 10MB allowed.")
        
        # Create safe filename
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if folder_path:
            full_path = f"{folder_path}/{safe_filename}"
        else:
            full_path = safe_filename
        
        async with httpx.AsyncClient() as client:
            # Upload file to file access server
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/write_file",
                json={"path": full_path, "content": content.decode('utf-8', errors='ignore')}
            )
            
            if response.status_code == 200:
                # Log the activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="upload",
                    filename=safe_filename,
                    status="success"
                )
                return {
                    "message": "File uploaded successfully",
                    "filename": safe_filename,
                    "size": len(content),
                    "path": full_path
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to upload file")
    except Exception as e:
        # Log error activity
        try:
            from src.services.activity_logger import ActivityLogger
            await ActivityLogger.log_file_operation(
                db=db,
                user_id=user.uuid,
                action="upload",
                filename=file.filename,
                status="error",
                details=str(e)
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.post("/files")
async def create_file(
    request: Request,
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Create a new file or folder"""
    try:
        # Parse JSON body
        body = await request.json()
        filename = body.get("name")
        content = body.get("content", "")
        is_folder = body.get("is_folder", False)
        
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        async with httpx.AsyncClient() as client:
            if is_folder:
                # Create folder by creating a file with folder marker
                response = await client.post(
                    f"{FILE_ACCESS_SERVER_URL}/execute/write_file",
                    json={"path": f"{filename}/.folder", "content": ""}
                )
            else:
                # Create regular file
                response = await client.post(
                    f"{FILE_ACCESS_SERVER_URL}/execute/write_file",
                    json={"path": filename, "content": content}
                )
            
            if response.status_code == 200:
                # Log the activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="create",
                    filename=filename,
                    status="success"
                )
                return {"message": "File created successfully", "filename": filename}
            else:
                # Log failed activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="create",
                    filename=filename,
                    status="error",
                    details=f"Failed with status {response.status_code}"
                )
                raise HTTPException(status_code=400, detail="Failed to create file")
    except Exception as e:
        # Log error activity
        try:
            from src.services.activity_logger import ActivityLogger
            await ActivityLogger.log_file_operation(
                db=db,
                user_id=user.uuid,
                action="create",
                filename=filename,
                status="error",
                details=str(e)
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error creating file: {str(e)}")

@router.get("/files/{filename}/read")
async def read_file(filename: str):
    """Read file content for viewing"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/read_file",
                json={"path": filename}
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Delete a file or folder"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/delete_file",
                json={"path": filename}
            )
            if response.status_code == 200:
                # Log the activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="delete",
                    filename=filename,
                    status="success"
                )
                return {"message": "File deleted successfully"}
            else:
                # Log failed activity
                from src.services.activity_logger import ActivityLogger
                await ActivityLogger.log_file_operation(
                    db=db,
                    user_id=user.uuid,
                    action="delete",
                    filename=filename,
                    status="error",
                    details=f"Failed with status {response.status_code}"
                )
                raise HTTPException(status_code=400, detail="Failed to delete file")
    except Exception as e:
        # Log error activity
        try:
            from src.services.activity_logger import ActivityLogger
            await ActivityLogger.log_file_operation(
                db=db,
                user_id=user.uuid,
                action="delete",
                filename=filename,
                status="error",
                details=str(e)
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
