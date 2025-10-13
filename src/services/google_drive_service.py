import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os

class GoogleDriveService:
    def __init__(self, user_token: str):
        self.user_token = user_token
        self.synapse_folder_id = None
        self.base_url = "https://www.googleapis.com/drive/v3"
        self.headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
    
    async def get_or_create_synapse_folder(self) -> str:
        """Get or create 'Synapse Sandbox' folder in Drive"""
        try:
            # Search for existing folder
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/files",
                    headers=self.headers,
                    params={
                        "q": "name='Synapse Sandbox' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                        "fields": "files(id, name, createdTime, modifiedTime)"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("files"):
                        self.synapse_folder_id = data["files"][0]["id"]
                        return self.synapse_folder_id
                
                # Create folder if not exists
                folder_metadata = {
                    "name": "Synapse Sandbox",
                    "mimeType": "application/vnd.google-apps.folder",
                    "description": "Synapse AI sandbox files and data"
                }
                
                response = await client.post(
                    f"{self.base_url}/files",
                    headers=self.headers,
                    json=folder_metadata
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.synapse_folder_id = data["id"]
                    return self.synapse_folder_id
                else:
                    raise Exception(f"Failed to create folder: {response.text}")
                    
        except Exception as e:
            print(f"Error in get_or_create_synapse_folder: {e}")
            raise e
    
    async def upload_file(self, filename: str, content: str, mime_type: str = 'text/plain') -> str:
        """Upload file to Synapse folder in Drive using simple upload method"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            # Check if file already exists
            existing_file_id = await self._find_file_by_name(filename)
            
            async with httpx.AsyncClient() as client:
                if existing_file_id:
                    # Update existing file using simple upload
                    response = await client.patch(
                        f"{self.base_url}/files/{existing_file_id}",
                        headers={
                            "Authorization": f"Bearer {self.user_token}",
                            "Content-Type": mime_type
                        },
                        content=content
                    )
                else:
                    # Create new file using simple upload with metadata in query params
                    file_metadata = {
                        "name": filename,
                        "parents": [self.synapse_folder_id]
                    }
                    
                    # Use simple upload with metadata as query parameters
                    response = await client.post(
                        f"{self.base_url}/files?uploadType=media",
                        headers={
                            "Authorization": f"Bearer {self.user_token}",
                            "Content-Type": mime_type
                        },
                        content=content,
                        params=file_metadata
                    )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return data["id"]
                else:
                    # If simple upload fails, try alternative approach
                    if not existing_file_id:
                        # Create file with metadata first, then upload content
                        metadata_response = await client.post(
                            f"{self.base_url}/files",
                            headers={
                                "Authorization": f"Bearer {self.user_token}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "name": filename,
                                "parents": [self.synapse_folder_id]
                            }
                        )
                        
                        if metadata_response.status_code in [200, 201]:
                            file_data = metadata_response.json()
                            file_id = file_data["id"]
                            
                            # Upload content to the created file
                            content_response = await client.patch(
                                f"{self.base_url}/files/{file_id}",
                                headers={
                                    "Authorization": f"Bearer {self.user_token}",
                                    "Content-Type": mime_type
                                },
                                content=content
                            )
                            
                            if content_response.status_code in [200, 201]:
                                return file_id
                            else:
                                raise Exception(f"Failed to upload content: {content_response.text}")
                        else:
                            raise Exception(f"Failed to create file metadata: {metadata_response.text}")
                    else:
                        raise Exception(f"Failed to update file: {response.text}")
                    
        except Exception as e:
            print(f"Error uploading file {filename}: {e}")
            raise e
    
    async def download_file(self, file_id: str) -> str:
        """Download file from Drive"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/files/{file_id}?alt=media",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.text
                else:
                    raise Exception(f"Failed to download file: {response.text}")
                    
        except Exception as e:
            print(f"Error downloading file {file_id}: {e}")
            raise e
    
    async def list_files(self) -> List[Dict[str, Any]]:
        """List all files in Synapse folder"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/files",
                    headers=self.headers,
                    params={
                        "q": f"'{self.synapse_folder_id}' in parents and trashed=false",
                        "fields": "files(id, name, size, createdTime, modifiedTime, mimeType)"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("files", [])
                else:
                    raise Exception(f"Failed to list files: {response.text}")
                    
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file from Drive"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/files/{file_id}",
                    headers=self.headers
                )
                
                return response.status_code == 204
                
        except Exception as e:
            print(f"Error deleting file {file_id}: {e}")
            return False
    
    async def _find_file_by_name(self, filename: str) -> Optional[str]:
        """Find file by name in Synapse folder"""
        try:
            if not self.synapse_folder_id:
                await self.get_or_create_synapse_folder()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/files",
                    headers=self.headers,
                    params={
                        "q": f"name='{filename}' and '{self.synapse_folder_id}' in parents and trashed=false",
                        "fields": "files(id)"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    files = data.get("files", [])
                    return files[0]["id"] if files else None
                else:
                    return None
                    
        except Exception as e:
            print(f"Error finding file {filename}: {e}")
            return None
    
    async def sync_from_drive(self, file_access_server_url: str) -> Dict[str, Any]:
        """Sync files from Drive to local sandbox"""
        try:
            drive_files = await self.list_files()
            synced_count = 0
            errors = []
            
            async with httpx.AsyncClient() as client:
                for file_info in drive_files:
                    try:
                        # Download file content from Drive
                        content = await self.download_file(file_info["id"])
                        
                        # Upload to local file access server
                        response = await client.post(
                            f"{file_access_server_url}/execute/write_file",
                            json={
                                "path": file_info["name"],
                                "content": content
                            }
                        )
                        
                        if response.status_code == 200:
                            synced_count += 1
                        else:
                            errors.append(f"Failed to sync {file_info['name']}: {response.text}")
                            
                    except Exception as e:
                        errors.append(f"Error syncing {file_info['name']}: {str(e)}")
            
            return {
                "success": True,
                "synced_count": synced_count,
                "total_files": len(drive_files),
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0,
                "total_files": 0,
                "errors": [str(e)]
            }
    
    async def sync_to_drive(self, file_access_server_url: str) -> Dict[str, Any]:
        """Sync local sandbox files to Drive"""
        try:
            # Get list of local files
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{file_access_server_url}/list_files")
                
                if response.status_code != 200:
                    raise Exception("Failed to get local files list")
                
                local_files = response.json().get("files", [])
                synced_count = 0
                errors = []
                
                for file_info in local_files:
                    try:
                        # Read file content from local server
                        content_response = await client.post(
                            f"{file_access_server_url}/execute/read_file",
                            json={"path": file_info["name"]}
                        )
                        
                        if content_response.status_code == 200:
                            content_data = content_response.json()
                            content = content_data.get("content", "")
                            
                            # Upload to Drive
                            file_id = await self.upload_file(file_info["name"], content)
                            synced_count += 1
                        else:
                            errors.append(f"Failed to read {file_info['name']}: {content_response.text}")
                            
                    except Exception as e:
                        errors.append(f"Error syncing {file_info['name']}: {str(e)}")
                
                return {
                    "success": True,
                    "synced_count": synced_count,
                    "total_files": len(local_files),
                    "errors": errors
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0,
                "total_files": 0,
                "errors": [str(e)]
            }
    
    async def bidirectional_sync(self, file_access_server_url: str) -> Dict[str, Any]:
        """Two-way sync between Drive and sandbox"""
        try:
            # Get timestamps from both sources
            drive_files = await self.list_files()
            local_files = []
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{file_access_server_url}/list_files")
                if response.status_code == 200:
                    local_files = response.json().get("files", [])
            
            # Create lookup dictionaries
            drive_lookup = {f["name"]: f for f in drive_files}
            local_lookup = {f["name"]: f for f in local_files}
            
            synced_to_drive = 0
            synced_from_drive = 0
            errors = []
            
            # Sync newer files from Drive to local
            for name, drive_file in drive_lookup.items():
                if name not in local_lookup:
                    # File exists only in Drive, sync to local
                    try:
                        content = await self.download_file(drive_file["id"])
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                f"{file_access_server_url}/execute/write_file",
                                json={"path": name, "content": content}
                            )
                            if response.status_code == 200:
                                synced_from_drive += 1
                    except Exception as e:
                        errors.append(f"Error syncing {name} from Drive: {str(e)}")
                else:
                    # Compare timestamps
                    drive_time = datetime.fromisoformat(drive_file["modifiedTime"].replace('Z', '+00:00'))
                    local_time = datetime.fromtimestamp(local_lookup[name]["modified"])
                    
                    if drive_time > local_time:
                        # Drive version is newer
                        try:
                            content = await self.download_file(drive_file["id"])
                            async with httpx.AsyncClient() as client:
                                response = await client.post(
                                    f"{file_access_server_url}/execute/write_file",
                                    json={"path": name, "content": content}
                                )
                                if response.status_code == 200:
                                    synced_from_drive += 1
                        except Exception as e:
                            errors.append(f"Error syncing {name} from Drive: {str(e)}")
            
            # Sync newer files from local to Drive
            for name, local_file in local_lookup.items():
                if name not in drive_lookup:
                    # File exists only locally, sync to Drive
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                f"{file_access_server_url}/execute/read_file",
                                json={"path": name}
                            )
                            if response.status_code == 200:
                                content_data = response.json()
                                content = content_data.get("content", "")
                                await self.upload_file(name, content)
                                synced_to_drive += 1
                    except Exception as e:
                        errors.append(f"Error syncing {name} to Drive: {str(e)}")
                else:
                    # Compare timestamps
                    drive_time = datetime.fromisoformat(drive_lookup[name]["modifiedTime"].replace('Z', '+00:00'))
                    local_time = datetime.fromtimestamp(local_file["modified"])
                    
                    if local_time > drive_time:
                        # Local version is newer
                        try:
                            async with httpx.AsyncClient() as client:
                                response = await client.post(
                                    f"{file_access_server_url}/execute/read_file",
                                    json={"path": name}
                                )
                                if response.status_code == 200:
                                    content_data = response.json()
                                    content = content_data.get("content", "")
                                    await self.upload_file(name, content)
                                    synced_to_drive += 1
                        except Exception as e:
                            errors.append(f"Error syncing {name} to Drive: {str(e)}")
            
            return {
                "success": True,
                "synced_to_drive": synced_to_drive,
                "synced_from_drive": synced_from_drive,
                "total_drive_files": len(drive_files),
                "total_local_files": len(local_files),
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "synced_to_drive": 0,
                "synced_from_drive": 0,
                "total_drive_files": 0,
                "total_local_files": 0,
                "errors": [str(e)]
            }
