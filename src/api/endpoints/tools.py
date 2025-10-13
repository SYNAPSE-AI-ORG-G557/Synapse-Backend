from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import httpx
import structlog

from src.core.dependencies import get_current_active_user
from src.db.session import get_db_session
from src.db import models

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])

@router.get("/status")
async def get_tools_status(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get the status of all integrated tools and services.
    """
    try:
        # Check Google connection status
        google_connected = bool(current_user.google_access_token)
        
        # Check if user has any active subscriptions
        daily_song_subscribed = current_user.daily_song_subscribed
        
        return {
            "google_connected": google_connected,
            "gmail_available": google_connected,
            "calendar_available": google_connected,
            "daily_song_subscribed": daily_song_subscribed,
            "automation_services": {
                "daily_song": {
                    "available": True,
                    "subscribed": daily_song_subscribed,
                    "description": "Daily song recommendations via email at 8 AM"
                }
            },
            "web_tools": {
                "web_search": {"available": True, "description": "Search the web for current information"},
                "weather": {"available": True, "description": "Get weather information for any location"},
                "browser_automation": {"available": True, "description": "Open websites and navigate automatically"}
            },
            "file_tools": {
                "file_operations": {"available": True, "description": "Create, read, and manage files"},
                "file_storage": {"available": True, "description": "Personal file storage space"}
            },
            "system_tools": {
                "reminders": {"available": True, "description": "Set reminders and notifications"},
                "multi_step_automation": {"available": True, "description": "Schedule complex workflows with timing"},
                "shell_commands": {"available": True, "description": "Execute terminal commands"}
            }
        }
    except Exception as e:
        log.error("Error getting tools status", error=str(e), user_id=current_user.uuid)
        raise HTTPException(status_code=500, detail="Failed to get tools status")

@router.post("/gmail/test")
async def test_gmail_integration(
    current_user: models.User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Test Gmail integration - now handled via direct WebSocket to Tooling Engine.
    """
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=400, 
            detail="Google account not connected. Please connect your Google account first."
        )
    
    return {
        "success": True,
        "message": "Gmail test should be initiated via WebSocket connection to Tooling Engine."
    }

@router.post("/calendar/test")
async def test_calendar_integration(
    current_user: models.User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Test Google Calendar integration - now handled via direct WebSocket to Tooling Engine.
    """
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=400, 
            detail="Google account not connected. Please connect your Google account first."
        )
    
    return {
        "success": True,
        "message": "Calendar test should be initiated via WebSocket connection to Tooling Engine."
    }

@router.post("/automation/subscribe")
async def subscribe_to_automation(
    service: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Subscribe to automation services.
    """
    if service == "daily_song":
        try:
            # Update user subscription status
            current_user.daily_song_subscribed = True
            await db.commit()
            
            return {
                "success": True,
                "message": "Successfully subscribed to daily song service. You will receive daily song emails at 8 AM.",
                "service": service,
                "subscribed": True
            }
        except Exception as e:
            log.error("Error subscribing to daily song service", error=str(e), user_id=current_user.uuid)
            raise HTTPException(status_code=500, detail="Failed to subscribe to service")
    else:
        raise HTTPException(status_code=400, detail="Unknown service")

@router.post("/automation/unsubscribe")
async def unsubscribe_from_automation(
    service: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Unsubscribe from automation services.
    """
    if service == "daily_song":
        try:
            # Update user subscription status
            current_user.daily_song_subscribed = False
            await db.commit()
            
            return {
                "success": True,
                "message": "Successfully unsubscribed from daily song service.",
                "service": service,
                "subscribed": False
            }
        except Exception as e:
            log.error("Error unsubscribing from daily song service", error=str(e), user_id=current_user.uuid)
            raise HTTPException(status_code=500, detail="Failed to unsubscribe from service")
    else:
        raise HTTPException(status_code=400, detail="Unknown service")

@router.get("/automation/subscriptions")
async def get_automation_subscriptions(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get user's automation service subscriptions.
    """
    return {
        "daily_song": {
            "subscribed": current_user.daily_song_subscribed,
            "description": "Daily song recommendations via email at 8 AM"
        }
    }

@router.post("/test/{tool_name}")
async def test_tool(
    tool_name: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Test various tools by creating conversations and sending test messages.
    """
    test_messages = {
        "web_search": "Search for the latest news about artificial intelligence",
        "weather": "What is the weather in Hyderabad today?",
        "browser": "Open YouTube in my browser",
        "files": "Create a file called test.txt with the content 'Hello from Synapse AI!'",
        "reminder": "Remind me to check my email in 30 seconds",
        "multi_step": "Open YouTube after 1 minute"
    }
    
    if tool_name not in test_messages:
        raise HTTPException(status_code=400, detail="Unknown tool")
    
    try:
        # Create a test conversation
        conversation = models.Conversation(
            user_id=current_user.uuid,
            title=f"{tool_name.title()} Test"
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        # Send test message
        message = models.ChatMessage(
            conversation_id=conversation.uuid,
            user_id=current_user.uuid,
            role="user",
            content=test_messages[tool_name]
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        # Forward message to orchestrator via Redis to trigger processing
        import redis
        import json
        import uuid
        
        redis_client = redis.Redis(host='redis', port=6379, db=0)
        job_id = str(uuid.uuid4())
        
        # Create job data
        job_data = {
            "job_id": job_id,
            "user_id": str(current_user.uuid),
            "conversation_id": str(conversation.uuid),
            "message_id": str(message.uuid),
            "content": message.content,
            "status": "PROCESSING"
        }
        
        # Publish to Redis channel
        redis_client.publish("job-updates", json.dumps(job_data))
        
        return {
            "success": True,
            "message": f"{tool_name.title()} test initiated. Check your conversation for results.",
            "conversation_id": conversation.uuid,
            "job_id": job_id,
            "test_message": test_messages[tool_name]
        }
    except Exception as e:
        log.error(f"Error testing {tool_name}", error=str(e), user_id=current_user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to test {tool_name}")
