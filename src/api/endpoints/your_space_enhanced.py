from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import httpx
import os
import shutil
import mimetypes
import base64
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

@router.post("/files/bulk-delete")
async def bulk_delete_files(
    request: Request,
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Delete multiple files at once"""
    try:
        body = await request.json()
        filenames = body.get("filenames", [])
        
        if not filenames:
            raise HTTPException(status_code=400, detail="No files specified for deletion")
        
        results = []
        async with httpx.AsyncClient() as client:
            for filename in filenames:
                try:
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
                            action="bulk_delete",
                            filename=filename,
                            status="success"
                        )
                        results.append({"filename": filename, "status": "success"})
                    else:
                        results.append({"filename": filename, "status": "error", "message": "Failed to delete"})
                except Exception as e:
                    results.append({"filename": filename, "status": "error", "message": str(e)})
        
        return {
            "message": f"Bulk delete completed. {len([r for r in results if r['status'] == 'success'])} files deleted successfully.",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in bulk delete: {str(e)}")

@router.get("/files/{filename}/preview")
async def preview_file(filename: str):
    """Get file preview for different file types"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/read_file",
                json={"path": filename}
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                
                # Determine file type and provide appropriate preview
                file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
                
                preview_data = {
                    "filename": filename,
                    "type": file_extension,
                    "size": len(content),
                    "preview": ""
                }
                
                # Generate preview based on file type
                if file_extension in ['txt', 'md', 'json', 'yaml', 'yml', 'xml', 'csv']:
                    # Text files - show first 1000 characters
                    preview_data["preview"] = content[:1000] + ("..." if len(content) > 1000 else "")
                elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                    # Image files - return base64 encoded content
                    preview_data["preview"] = f"data:image/{file_extension};base64,{base64.b64encode(content.encode()).decode()}"
                elif file_extension in ['pdf']:
                    preview_data["preview"] = "PDF file - preview not available"
                else:
                    preview_data["preview"] = f"Binary file ({file_extension}) - preview not available"
                
                return preview_data
            else:
                raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")

@router.post("/files/{filename}/rename")
async def rename_file(
    filename: str,
    request: Request,
    user = Depends(get_current_user_sync),
    db: Session = Depends(get_sync_db_session)
):
    """Rename a file or folder"""
    try:
        body = await request.json()
        new_name = body.get("new_name")
        
        if not new_name:
            raise HTTPException(status_code=400, detail="New name is required")
        
        async with httpx.AsyncClient() as client:
            # Read the original file
            read_response = await client.post(
                f"{FILE_ACCESS_SERVER_URL}/execute/read_file",
                json={"path": filename}
            )
            
            if read_response.status_code == 200:
                content = read_response.json().get("content", "")
                
                # Create new file with new name
                create_response = await client.post(
                    f"{FILE_ACCESS_SERVER_URL}/execute/write_file",
                    json={"path": new_name, "content": content}
                )
                
                if create_response.status_code == 200:
                    # Delete original file
                    delete_response = await client.post(
                        f"{FILE_ACCESS_SERVER_URL}/execute/delete_file",
                        json={"path": filename}
                    )
                    
                    if delete_response.status_code == 200:
                        # Log the activity
                        from src.services.activity_logger import ActivityLogger
                        await ActivityLogger.log_file_operation(
                            db=db,
                            user_id=user.uuid,
                            action="rename",
                            filename=f"{filename} -> {new_name}",
                            status="success"
                        )
                        return {"message": "File renamed successfully", "old_name": filename, "new_name": new_name}
                    else:
                        raise HTTPException(status_code=400, detail="Failed to delete original file")
                else:
                    raise HTTPException(status_code=400, detail="Failed to create file with new name")
            else:
                raise HTTPException(status_code=404, detail="Original file not found")
    except Exception as e:
        # Log error activity
        try:
            from src.services.activity_logger import ActivityLogger
            await ActivityLogger.log_file_operation(
                db=db,
                user_id=user.uuid,
                action="rename",
                filename=filename,
                status="error",
                details=str(e)
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error renaming file: {str(e)}")

@router.get("/files/stats")
async def get_file_stats(user = Depends(get_current_user_sync)):
    """Get file storage statistics"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{FILE_ACCESS_SERVER_URL}/list_files")
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                total_files = len(files)
                total_size = sum(file_info.get("size", 0) for file_info in files)
                file_types = {}
                
                for file_info in files:
                    file_type = file_info.get("type", "unknown")
                    file_types[file_type] = file_types.get(file_type, 0) + 1
                
                return {
                    "total_files": total_files,
                    "total_size": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "file_types": file_types,
                    "last_updated": datetime.now().isoformat()
                }
            else:
                return {
                    "total_files": 0,
                    "total_size": 0,
                    "total_size_mb": 0,
                    "file_types": {},
                    "last_updated": datetime.now().isoformat()
                }
    except Exception as e:
        return {
            "total_files": 0,
            "total_size": 0,
            "total_size_mb": 0,
            "file_types": {},
            "last_updated": datetime.now().isoformat(),
            "error": str(e)
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

@router.get("/files/search")
async def search_files(
    query: str,
    file_type: str = "",
    user = Depends(get_current_user_sync)
):
    """Search files by name or content"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{FILE_ACCESS_SERVER_URL}/list_files")
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                # Filter files based on search query
                matching_files = []
                for file_info in files:
                    # Search in filename
                    if query.lower() in file_info["name"].lower():
                        matching_files.append(file_info)
                    # Search in file type
                    elif file_type and file_info.get("type") == file_type:
                        matching_files.append(file_info)
                
                return {
                    "query": query,
                    "results": matching_files,
                    "total_matches": len(matching_files)
                }
            else:
                return {"query": query, "results": [], "total_matches": 0}
    except Exception as e:
        return {"query": query, "results": [], "total_matches": 0, "error": str(e)}

