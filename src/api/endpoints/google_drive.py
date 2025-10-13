from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import httpx
from src.core.config import settings
from src.core.dependencies import get_current_user_sync
from src.services.google_drive_service import GoogleDriveService

router = APIRouter()

# File Access Server Configuration
FILE_ACCESS_SERVER_URL = "http://file_access_server:8002"

@router.post("/enable-sync")
async def enable_drive_sync(user = Depends(get_current_user_sync)):
    """Enable automatic Google Drive sync for user's sandbox"""
    try:
        # Check if user has Google OAuth token
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        # Initialize Google Drive service
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Create or get Synapse folder
        folder_id = await drive_service.get_or_create_synapse_folder()
        
        # Set sync_enabled flag in user preferences (you'll need to implement this)
        # For now, we'll just return success
        
        return {
            "success": True,
            "message": "Google Drive sync enabled successfully",
            "folder_id": folder_id,
            "folder_name": "Synapse Sandbox"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable sync: {str(e)}")

@router.post("/sync-now")
async def sync_now(user = Depends(get_current_user_sync)):
    """Manually trigger bidirectional sync"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Ensure folder exists
        await drive_service.get_or_create_synapse_folder()
        
        # Run bidirectional sync
        result = await drive_service.bidirectional_sync(FILE_ACCESS_SERVER_URL)
        
        return {
            "success": result["success"],
            "message": "Sync completed",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/status")
async def get_sync_status(user = Depends(get_current_user_sync)):
    """Get current sync status and last sync time"""
    try:
        if not user.google_access_token:
            return {
                "connected": False,
                "message": "Google account not connected",
                "sync_enabled": False
            }
        
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Get folder info
        folder_id = await drive_service.get_or_create_synapse_folder()
        files = await drive_service.list_files()
        
        return {
            "connected": True,
            "sync_enabled": True,
            "folder_id": folder_id,
            "folder_name": "Synapse Sandbox",
            "file_count": len(files),
            "last_sync": "Manual sync only",  # You can implement last sync tracking
            "files": files[:10]  # Return first 10 files as preview
        }
        
    except Exception as e:
        return {
            "connected": False,
            "message": f"Error checking status: {str(e)}",
            "sync_enabled": False
        }

@router.post("/disable-sync")
async def disable_drive_sync(user = Depends(get_current_user_sync)):
    """Disable Google Drive sync"""
    try:
        # Set sync_enabled flag to false in user preferences
        # For now, we'll just return success
        
        return {
            "success": True,
            "message": "Google Drive sync disabled successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable sync: {str(e)}")

@router.post("/upload-file")
async def upload_file_to_drive(
    filename: str,
    content: str,
    user = Depends(get_current_user_sync)
):
    """Upload a specific file to Google Drive"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Ensure folder exists
        await drive_service.get_or_create_synapse_folder()
        
        # Upload file
        file_id = await drive_service.upload_file(filename, content)
        
        return {
            "success": True,
            "message": f"File {filename} uploaded to Drive successfully",
            "file_id": file_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/download-file/{file_id}")
async def download_file_from_drive(
    file_id: str,
    user = Depends(get_current_user_sync)
):
    """Download a specific file from Google Drive"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Download file
        content = await drive_service.download_file(file_id)
        
        return {
            "success": True,
            "content": content,
            "file_id": file_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.get("/list-files")
async def list_drive_files(user = Depends(get_current_user_sync)):
    """List all files in the Synapse Drive folder"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Ensure folder exists
        await drive_service.get_or_create_synapse_folder()
        
        # List files
        files = await drive_service.list_files()
        
        return {
            "success": True,
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.delete("/delete-file/{file_id}")
async def delete_drive_file(
    file_id: str,
    user = Depends(get_current_user_sync)
):
    """Delete a file from Google Drive"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Delete file
        success = await drive_service.delete_file(file_id)
        
        if success:
            return {
                "success": True,
                "message": f"File {file_id} deleted from Drive successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.post("/sync-from-drive")
async def sync_from_drive(user = Depends(get_current_user_sync)):
    """Sync files from Drive to local sandbox"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Ensure folder exists
        await drive_service.get_or_create_synapse_folder()
        
        # Sync from Drive
        result = await drive_service.sync_from_drive(FILE_ACCESS_SERVER_URL)
        
        return {
            "success": result["success"],
            "message": "Sync from Drive completed",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync from Drive failed: {str(e)}")

@router.post("/sync-to-drive")
async def sync_to_drive(user = Depends(get_current_user_sync)):
    """Sync files from local sandbox to Drive"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveService(user.google_access_token)
        
        # Ensure folder exists
        await drive_service.get_or_create_synapse_folder()
        
        # Sync to Drive
        result = await drive_service.sync_to_drive(FILE_ACCESS_SERVER_URL)
        
        return {
            "success": result["success"],
            "message": "Sync to Drive completed",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync to Drive failed: {str(e)}")
