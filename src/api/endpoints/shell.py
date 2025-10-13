from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import httpx
import json
from src.core.config import settings

router = APIRouter()

# Shell Server Configuration
SHELL_SERVER_URL = "http://shell_server:8004"

@router.post("/execute")
async def execute_shell_command(command: str):
    """Execute shell command via shell MCP server"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SHELL_SERVER_URL}/execute",
                json={"command": command},
                timeout=30.0  # 30 second timeout for commands
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "output": data.get("output", ""),
                    "exit_code": data.get("exit_code", 0),
                    "command": command
                }
            else:
                return {
                    "success": False,
                    "output": f"Command failed with status {response.status_code}",
                    "exit_code": 1,
                    "command": command
                }
    except httpx.TimeoutException:
        return {
            "success": False,
            "output": "Command timed out after 30 seconds",
            "exit_code": 124,
            "command": command
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Error executing command: {str(e)}",
            "exit_code": 1,
            "command": command
        }

@router.post("/ai-command")
async def generate_command_from_ai(request: str):
    """Ask LLM to generate shell command from natural language"""
    try:
        # For now, we'll use a simple mapping of common requests to commands
        # In a real implementation, this would call an LLM service
        command_mapping = {
            "list all files": "ls -la",
            "list files": "ls -la",
            "show files": "ls -la",
            "current directory": "pwd",
            "where am i": "pwd",
            "disk usage": "df -h",
            "disk space": "df -h",
            "memory usage": "free -h",
            "memory": "free -h",
            "running processes": "ps aux",
            "processes": "ps aux",
            "system info": "uname -a",
            "system information": "uname -a",
            "current time": "date",
            "time": "date",
            "current user": "whoami",
            "who am i": "whoami",
            "network connections": "netstat -tuln",
            "network": "netstat -tuln",
            "environment variables": "env",
            "environment": "env",
            "uptime": "uptime",
            "load average": "uptime",
            "cpu info": "lscpu",
            "cpu": "lscpu",
            "kernel version": "uname -r",
            "kernel": "uname -r"
        }
        
        # Simple keyword matching
        request_lower = request.lower()
        suggested_command = None
        
        for keyword, command in command_mapping.items():
            if keyword in request_lower:
                suggested_command = command
                break
        
        if not suggested_command:
            # Default fallback commands based on common patterns
            if any(word in request_lower for word in ["file", "list", "show", "dir"]):
                suggested_command = "ls -la"
            elif any(word in request_lower for word in ["directory", "folder", "path", "where"]):
                suggested_command = "pwd"
            elif any(word in request_lower for word in ["disk", "space", "storage"]):
                suggested_command = "df -h"
            elif any(word in request_lower for word in ["memory", "ram"]):
                suggested_command = "free -h"
            elif any(word in request_lower for word in ["process", "running", "task"]):
                suggested_command = "ps aux"
            elif any(word in request_lower for word in ["system", "info", "information"]):
                suggested_command = "uname -a"
            elif any(word in request_lower for word in ["time", "date", "clock"]):
                suggested_command = "date"
            elif any(word in request_lower for word in ["user", "who"]):
                suggested_command = "whoami"
            else:
                suggested_command = "ls -la"  # Default fallback
        
        return {
            "success": True,
            "command": suggested_command,
            "request": request,
            "explanation": f"Based on your request '{request}', I suggest running: {suggested_command}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "command": "ls -la",
            "request": request,
            "explanation": f"Error generating command: {str(e)}"
        }

@router.get("/status")
async def get_shell_status():
    """Get shell server status"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SHELL_SERVER_URL}/status", timeout=5.0)
            
            if response.status_code == 200:
                return {
                    "status": "online",
                    "server_url": SHELL_SERVER_URL,
                    "response": response.json()
                }
            else:
                return {
                    "status": "error",
                    "server_url": SHELL_SERVER_URL,
                    "error": f"Server returned status {response.status_code}"
                }
    except Exception as e:
        return {
            "status": "offline",
            "server_url": SHELL_SERVER_URL,
            "error": str(e)
        }
