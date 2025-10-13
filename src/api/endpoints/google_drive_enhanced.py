from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from src.core.dependencies import get_current_user_sync
from src.services.google_drive_enhanced import GoogleDriveEnhancedService
import structlog
import tempfile
import os

log = structlog.get_logger(__name__)
router = APIRouter()

# Pydantic models for request validation
class CreateFolderRequest(BaseModel):
    folder_name: str
    parent_folder_id: Optional[str] = None

class ShareFileRequest(BaseModel):
    file_id: str
    email: str
    role: Optional[str] = 'reader'
    notify: Optional[bool] = True

class CopyFileRequest(BaseModel):
    file_id: str
    new_name: Optional[str] = None
    destination_folder_id: Optional[str] = None

class MoveFileRequest(BaseModel):
    file_id: str
    destination_folder_id: str

class SearchFilesRequest(BaseModel):
    query: str
    folder_id: Optional[str] = None

@router.post("/upload-file-enhanced")
async def upload_file_enhanced(
    file: UploadFile = File(...),
    folder_id: str = None,
    convert: bool = False,
    user = Depends(get_current_user_sync)
):
    """Upload file using enhanced PyDrive2 functionality"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            drive_service = GoogleDriveEnhancedService(user.google_access_token)
            result = await drive_service.upload_file_enhanced(
                file_path=temp_file_path,
                filename=file.filename,
                folder_id=folder_id,
                convert=convert
            )
            
            if result["success"]:
                log.info("File uploaded successfully using enhanced service", 
                        user_id=user.uuid, 
                        file_id=result["file_id"])
                return result
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except Exception as e:
        log.error("Error uploading file with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@router.post("/download-file-enhanced")
async def download_file_enhanced(
    request: Request,
    user = Depends(get_current_user_sync)
):
    """Download file using enhanced PyDrive2 functionality"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        body = await request.json()
        file_id = body.get("file_id")
        download_path = body.get("download_path")
        
        if not file_id:
            raise HTTPException(status_code=400, detail="file_id is required")
        
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.download_file_enhanced(file_id, download_path)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error downloading file with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@router.post("/list-files-enhanced")
async def list_files_enhanced(
    request: Request,
    user = Depends(get_current_user_sync)
):
    """List files with enhanced filtering using PyDrive2"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        body = await request.json()
        folder_id = body.get("folder_id")
        query = body.get("query")
        
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.list_files_enhanced(folder_id, query)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error listing files with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.post("/create-folder-enhanced")
async def create_folder_enhanced(
    request: CreateFolderRequest,
    user = Depends(get_current_user_sync)
):
    """Create a new folder using enhanced PyDrive2 functionality"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.create_folder_enhanced(
            folder_name=request.folder_name,
            parent_folder_id=request.parent_folder_id
        )
        
        if result["success"]:
            log.info("Folder created successfully using enhanced service", 
                    user_id=user.uuid, 
                    folder_id=result["folder_id"])
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error creating folder with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to create folder: {str(e)}")

@router.post("/share-file-enhanced")
async def share_file_enhanced(
    request: ShareFileRequest,
    user = Depends(get_current_user_sync)
):
    """Share file with specific permissions using enhanced PyDrive2 functionality"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.share_file_enhanced(
            file_id=request.file_id,
            email=request.email,
            role=request.role,
            notify=request.notify
        )
        
        if result["success"]:
            log.info("File shared successfully using enhanced service", 
                    user_id=user.uuid, 
                    file_id=request.file_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error sharing file with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to share file: {str(e)}")

@router.post("/copy-file-enhanced")
async def copy_file_enhanced(
    request: CopyFileRequest,
    user = Depends(get_current_user_sync)
):
    """Copy file to another location using enhanced PyDrive2 functionality"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.copy_file_enhanced(
            file_id=request.file_id,
            new_name=request.new_name,
            destination_folder_id=request.destination_folder_id
        )
        
        if result["success"]:
            log.info("File copied successfully using enhanced service", 
                    user_id=user.uuid, 
                    file_id=request.file_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error copying file with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to copy file: {str(e)}")

@router.post("/move-file-enhanced")
async def move_file_enhanced(
    request: MoveFileRequest,
    user = Depends(get_current_user_sync)
):
    """Move file to another folder using enhanced PyDrive2 functionality"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.move_file_enhanced(
            file_id=request.file_id,
            destination_folder_id=request.destination_folder_id
        )
        
        if result["success"]:
            log.info("File moved successfully using enhanced service", 
                    user_id=user.uuid, 
                    file_id=request.file_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error moving file with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to move file: {str(e)}")

@router.get("/file-metadata-enhanced/{file_id}")
async def get_file_metadata_enhanced(
    file_id: str,
    user = Depends(get_current_user_sync)
):
    """Get detailed file metadata using enhanced PyDrive2 functionality"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.get_file_metadata_enhanced(file_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error getting file metadata with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to get file metadata: {str(e)}")

@router.post("/search-files-enhanced")
async def search_files_enhanced(
    request: SearchFilesRequest,
    user = Depends(get_current_user_sync)
):
    """Search files with advanced query using enhanced PyDrive2 functionality"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.search_files_enhanced(
            query=request.query,
            folder_id=request.folder_id
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error searching files with enhanced service", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to search files: {str(e)}")

@router.get("/status-enhanced")
async def get_enhanced_drive_status(user = Depends(get_current_user_sync)):
    """Get enhanced Google Drive integration status"""
    try:
        if not user.google_access_token:
            return {
                "connected": False,
                "message": "Google account not connected",
                "enhanced_enabled": False
            }
        
        # Test enhanced connection
        drive_service = GoogleDriveEnhancedService(user.google_access_token)
        result = await drive_service.get_or_create_synapse_folder()
        
        if result:
            return {
                "connected": True,
                "enhanced_enabled": True,
                "synapse_folder_id": result,
                "message": "Enhanced Google Drive integration is working"
            }
        else:
            return {
                "connected": True,
                "enhanced_enabled": False,
                "message": "Enhanced Drive integration error"
            }
        
    except Exception as e:
        return {
            "connected": False,
            "enhanced_enabled": False,
            "message": f"Error checking enhanced Drive status: {str(e)}"
        }

