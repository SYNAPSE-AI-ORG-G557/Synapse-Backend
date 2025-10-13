"""
Browser Automation Proxy Endpoint
Proxies requests to the browser_server to avoid CORS issues
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import logging

from src.core.dependencies import get_current_user
from src.db.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

BROWSER_SERVER_URL = "http://browser_server:8005"

class BrowserSessionRequest(BaseModel):
    user_request: str
    visual_session: bool = True
    user_id: Optional[str] = None
    user_auth_token: Optional[str] = None

@router.post("/live-session")
async def create_live_browser_session(
    request: BrowserSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Proxy endpoint to create a live browser automation session.
    Forwards the request to browser_server to avoid CORS issues.
    """
    try:
        # Use current user's ID
        request.user_id = str(current_user.uuid)
        
        logger.info(f"🎥 Creating live browser session for user {current_user.uuid}")
        logger.info(f"🎥 User request: {request.user_request}")
        logger.info(f"🎥 Visual session: {request.visual_session}")
        
        payload = {
            "user_request": request.user_request,
            "visual_session": True,  # ALWAYS True for live browser!
            "user_id": request.user_id,
            "user_auth_token": request.user_auth_token
        }
        
        logger.info(f"📤 Sending to browser_server: {payload}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BROWSER_SERVER_URL}/execute/browser_automation",
                json=payload
            )
            
            logger.info(f"📥 Browser_server response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Live browser session created: {data.get('session_id')}")
                logger.info(f"📦 Full response: {data}")
                return data
            else:
                logger.error(f"❌ Browser server error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Browser server error: {response.text}"
                )
                
    except httpx.TimeoutException:
        logger.error("❌ Browser server timeout")
        raise HTTPException(status_code=504, detail="Browser server timeout")
    except httpx.RequestError as e:
        logger.error(f"❌ Browser server connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to browser server: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/screenshot/{filename}")
async def get_screenshot(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Proxy endpoint to fetch screenshots from browser_server.
    This allows the frontend to display automation screenshots.
    """
    try:
        logger.info(f"📸 Fetching screenshot: {filename} for user {current_user.uuid}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BROWSER_SERVER_URL}/screenshots/{filename}"
            )
            
            if response.status_code == 200:
                return StreamingResponse(
                    iter([response.content]),
                    media_type="image/png",
                    headers={"Content-Disposition": f"inline; filename={filename}"}
                )
            else:
                logger.error(f"❌ Screenshot not found: {filename}")
                raise HTTPException(status_code=404, detail="Screenshot not found")
                
    except httpx.RequestError as e:
        logger.error(f"❌ Browser server connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to browser server: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

