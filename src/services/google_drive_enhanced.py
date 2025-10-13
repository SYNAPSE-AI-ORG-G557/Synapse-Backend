import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from google.oauth2.credentials import Credentials
import structlog

log = structlog.get_logger(__name__)

class GoogleDriveEnhancedService:
    def __init__(self, user_token: str):
        self.user_token = user_token
        self.gauth = None
        self.drive = None
        self.synapse_folder_id = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize PyDrive2 client with user credentials"""
        try:
            # Create credentials object from user token
            credentials = Credentials(
                token=self.user_token,
                scopes=[
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.file'
                ]
            )
            
            # Initialize GoogleAuth with credentials
            self.gauth = GoogleAuth()
            self.gauth.credentials = credentials
            
            # Initialize GoogleDrive
            self.drive = GoogleDrive(self.gauth)
            log.info("Enhanced Google Drive client initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize enhanced Google Drive client: {str(e)}")
            raise e
    
    async def get_or_create_synapse_folder(self) -> str:
        """Get or create 'Synapse Sandbox' folder in Drive using PyDrive2"""
        try:
            # Search for existing folder
            file_list = self.drive.ListFile({
                'q': "title='Synapse Sandbox' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            }).GetList()
            
            if file_list:
                self.synapse_folder_id = file_list[0]['id']
                return self.synapse_folder_id
            
            # Create folder if not exists
            folder_metadata = {
                'title': 'Synapse Sandbox',
                'mimeType': 'application/vnd.google-apps.folder',
                'description': 'Synapse AI sandbox files and data'
            }
            
            folder = self.drive.CreateFile(folder_metadata)
            folder.Upload()
            
            self.synapse_folder_id = folder['id']
            return self.synapse_folder_id
            
        except Exception as e:
            log.error(f"Error in get_or_create_synapse_folder: {e}")
            raise e
    
    async def upload_file_enhanced(self, file_path: str, filename: str = None, 
                                  folder_id: str = None, convert: bool = False) -> Dict[str, Any]:
        """Upload file using PyDrive2 with enhanced features"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            if not filename:
                filename = os.path.basename(file_path)
            
            target_folder_id = folder_id or self.synapse_folder_id
            
            # Check if file already exists
            existing_file = await self._find_file_by_name(filename, target_folder_id)
            
            if existing_file:
                # Update existing file
                file_drive = self.drive.CreateFile({'id': existing_file['id']})
                file_drive.SetContentFile(file_path)
                file_drive.Upload()
                
                return {
                    "success": True,
                    "file_id": existing_file['id'],
                    "action": "updated",
                    "filename": filename
                }
            else:
                # Create new file
                file_drive = self.drive.CreateFile({
                    'title': filename,
                    'parents': [{'id': target_folder_id}]
                })
                
                file_drive.SetContentFile(file_path)
                file_drive.Upload()
                
                return {
                    "success": True,
                    "file_id": file_drive['id'],
                    "action": "created",
                    "filename": filename
                }
                
        except Exception as e:
            log.error(f"Error uploading file {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def download_file_enhanced(self, file_id: str, download_path: str = None) -> Dict[str, Any]:
        """Download file using PyDrive2 with enhanced features"""
        try:
            file_drive = self.drive.CreateFile({'id': file_id})
            
            if download_path:
                file_drive.GetContentFile(download_path)
                return {
                    "success": True,
                    "download_path": download_path,
                    "filename": file_drive['title']
                }
            else:
                # Return content as string
                content = file_drive.GetContentString()
                return {
                    "success": True,
                    "content": content,
                    "filename": file_drive['title']
                }
                
        except Exception as e:
            log.error(f"Error downloading file {file_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_files_enhanced(self, folder_id: str = None, 
                                 query: str = None) -> Dict[str, Any]:
        """List files with enhanced filtering using PyDrive2"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            target_folder_id = folder_id or self.synapse_folder_id
            
            # Build query
            if query:
                search_query = f"'{target_folder_id}' in parents and trashed=false and title contains '{query}'"
            else:
                search_query = f"'{target_folder_id}' in parents and trashed=false"
            
            file_list = self.drive.ListFile({'q': search_query}).GetList()
            
            files = []
            for file_drive in file_list:
                files.append({
                    'id': file_drive['id'],
                    'title': file_drive['title'],
                    'mimeType': file_drive['mimeType'],
                    'size': file_drive.get('fileSize', '0'),
                    'createdDate': file_drive['createdDate'],
                    'modifiedDate': file_drive['modifiedDate'],
                    'downloadUrl': file_drive.get('downloadUrl', ''),
                    'webViewLink': file_drive.get('webViewLink', ''),
                    'is_folder': file_drive['mimeType'] == 'application/vnd.google-apps.folder'
                })
            
            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
            
        except Exception as e:
            log.error(f"Error listing files: {e}")
            return {
                "success": False,
                "error": str(e),
                "files": [],
                "count": 0
            }
    
    async def create_folder_enhanced(self, folder_name: str, parent_folder_id: str = None) -> Dict[str, Any]:
        """Create a new folder using PyDrive2"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            target_parent_id = parent_folder_id or self.synapse_folder_id
            
            folder_metadata = {
                'title': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [{'id': target_parent_id}]
            }
            
            folder = self.drive.CreateFile(folder_metadata)
            folder.Upload()
            
            return {
                "success": True,
                "folder_id": folder['id'],
                "folder_name": folder_name
            }
            
        except Exception as e:
            log.error(f"Error creating folder {folder_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def share_file_enhanced(self, file_id: str, email: str, 
                                 role: str = 'reader', notify: bool = True) -> Dict[str, Any]:
        """Share file with specific permissions using PyDrive2"""
        try:
            file_drive = self.drive.CreateFile({'id': file_id})
            
            # Add permission
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            file_drive.InsertPermission(permission)
            
            return {
                "success": True,
                "message": f"File shared with {email} as {role}",
                "file_id": file_id
            }
            
        except Exception as e:
            log.error(f"Error sharing file {file_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def copy_file_enhanced(self, file_id: str, new_name: str = None, 
                                destination_folder_id: str = None) -> Dict[str, Any]:
        """Copy file to another location using PyDrive2"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            target_folder_id = destination_folder_id or self.synapse_folder_id
            
            # Get original file
            original_file = self.drive.CreateFile({'id': file_id})
            
            # Create copy
            copied_file = self.drive.CreateFile({
                'title': new_name or f"Copy of {original_file['title']}",
                'parents': [{'id': target_folder_id}]
            })
            
            copied_file.SetContentFile(original_file.GetContentFile())
            copied_file.Upload()
            
            return {
                "success": True,
                "copied_file_id": copied_file['id'],
                "original_file_id": file_id,
                "new_name": copied_file['title']
            }
            
        except Exception as e:
            log.error(f"Error copying file {file_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def move_file_enhanced(self, file_id: str, destination_folder_id: str) -> Dict[str, Any]:
        """Move file to another folder using PyDrive2"""
        try:
            file_drive = self.drive.CreateFile({'id': file_id})
            
            # Get current parents
            current_parents = file_drive['parents']
            
            # Remove from current parents and add to new parent
            file_drive['parents'] = [{'id': destination_folder_id}]
            file_drive.Upload()
            
            return {
                "success": True,
                "file_id": file_id,
                "moved_to_folder": destination_folder_id
            }
            
        except Exception as e:
            log.error(f"Error moving file {file_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_file_metadata_enhanced(self, file_id: str) -> Dict[str, Any]:
        """Get detailed file metadata using PyDrive2"""
        try:
            file_drive = self.drive.CreateFile({'id': file_id})
            
            return {
                "success": True,
                "metadata": {
                    'id': file_drive['id'],
                    'title': file_drive['title'],
                    'mimeType': file_drive['mimeType'],
                    'size': file_drive.get('fileSize', '0'),
                    'createdDate': file_drive['createdDate'],
                    'modifiedDate': file_drive['modifiedDate'],
                    'downloadUrl': file_drive.get('downloadUrl', ''),
                    'webViewLink': file_drive.get('webViewLink', ''),
                    'description': file_drive.get('description', ''),
                    'parents': file_drive.get('parents', []),
                    'owners': file_drive.get('owners', []),
                    'permissions': file_drive.get('permissions', [])
                }
            }
            
        except Exception as e:
            log.error(f"Error getting file metadata {file_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_files_enhanced(self, query: str, folder_id: str = None) -> Dict[str, Any]:
        """Search files with advanced query using PyDrive2"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            target_folder_id = folder_id or self.synapse_folder_id
            
            # Build search query
            search_query = f"'{target_folder_id}' in parents and trashed=false and (title contains '{query}' or fullText contains '{query}')"
            
            file_list = self.drive.ListFile({'q': search_query}).GetList()
            
            results = []
            for file_drive in file_list:
                results.append({
                    'id': file_drive['id'],
                    'title': file_drive['title'],
                    'mimeType': file_drive['mimeType'],
                    'size': file_drive.get('fileSize', '0'),
                    'modifiedDate': file_drive['modifiedDate'],
                    'webViewLink': file_drive.get('webViewLink', '')
                })
            
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "query": query
            }
            
        except Exception as e:
            log.error(f"Error searching files: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "count": 0
            }
    
    async def _find_file_by_name(self, filename: str, folder_id: str = None) -> Optional[Dict[str, Any]]:
        """Find file by name in specific folder using PyDrive2"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            target_folder_id = folder_id or self.synapse_folder_id
            
            file_list = self.drive.ListFile({
                'q': f"title='{filename}' and '{target_folder_id}' in parents and trashed=false"
            }).GetList()
            
            return file_list[0] if file_list else None
            
        except Exception as e:
            log.error(f"Error finding file {filename}: {e}")
            return None

