# System Health Check Endpoint
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import httpx
import asyncio
import structlog
from datetime import datetime

from src.core.dependencies import get_current_active_user

router = APIRouter(prefix="/system", tags=["System Health"])
log = structlog.get_logger(__name__)

# MCP Service URLs
MCP_SERVICES = {
    "web_search": "http://web_search_server:8001",
    "file_access": "http://file_access_server:8002", 
    "reminder": "http://reminder_server:8003",
    "shell": "http://shell_server:8004",
    "browser": "http://browser_server:8005",
    "weather": "http://weather_server:8006",
    "google_calendar": "http://google_calendar_server:8007",
    "gmail": "http://gmail_server:8008",
    "jarvis_automation": "http://jarvis_automation_server:8009",
    "google_drive": "http://google_drive_server:8013",
    "google_sheets": "http://google_sheets_server:8011"
}

@router.get("/health")
async def system_health_check(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Comprehensive system health check for all MCP services"""
    log.info("Starting system health check", user_id=current_user["uuid"])
    
    health_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "healthy",
        "services": {},
        "backend_services": {},
        "frontend_connectivity": "unknown"
    }
    
    # Check MCP Services
    async def check_service(service_name: str, base_url: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try to ping the service
                response = await client.get(f"{base_url}/health", timeout=5.0)
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds(),
                        "details": "Service responding"
                    }
                else:
                    return {
                        "status": "degraded",
                        "response_time": response.elapsed.total_seconds(),
                        "details": f"HTTP {response.status_code}"
                    }
        except httpx.ConnectError:
            return {
                "status": "unhealthy",
                "response_time": None,
                "details": "Connection refused"
            }
        except httpx.TimeoutException:
            return {
                "status": "unhealthy", 
                "response_time": None,
                "details": "Request timeout"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "response_time": None,
                "details": f"Error: {str(e)}"
            }
    
    # Check all MCP services concurrently
    service_tasks = [
        check_service(name, url) for name, url in MCP_SERVICES.items()
    ]
    service_results = await asyncio.gather(*service_tasks, return_exceptions=True)
    
    # Process results
    unhealthy_count = 0
    for i, (service_name, _) in enumerate(MCP_SERVICES.items()):
        result = service_results[i]
        if isinstance(result, Exception):
            health_results["services"][service_name] = {
                "status": "unhealthy",
                "response_time": None,
                "details": f"Exception: {str(result)}"
            }
            unhealthy_count += 1
        else:
            health_results["services"][service_name] = result
            if result["status"] == "unhealthy":
                unhealthy_count += 1
    
    # Check Backend Services
    backend_services = {
        "database": "postgresql://user:password@postgres:5432/synapse",
        "redis": "redis://redis:6379",
        "celery_worker": "celery_worker",
        "response_formatter": "internal"
    }
    
    # Database check
    try:
        from src.db.session import get_sync_db_session
        db = next(get_sync_db_session())
        db.execute("SELECT 1")
        health_results["backend_services"]["database"] = {
            "status": "healthy",
            "details": "Connection successful"
        }
    except Exception as e:
        health_results["backend_services"]["database"] = {
            "status": "unhealthy",
            "details": f"Connection failed: {str(e)}"
        }
        unhealthy_count += 1
    
    # Redis check
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, decode_responses=True)
        r.ping()
        health_results["backend_services"]["redis"] = {
            "status": "healthy",
            "details": "Connection successful"
        }
    except Exception as e:
        health_results["backend_services"]["redis"] = {
            "status": "unhealthy",
            "details": f"Connection failed: {str(e)}"
        }
        unhealthy_count += 1
    
    # Response formatter check
    try:
        from src.services.response_formatter import ResponseFormatter
        formatter = ResponseFormatter()
        test_result = formatter.format_general_response("test")
        health_results["backend_services"]["response_formatter"] = {
            "status": "healthy",
            "details": "Service available"
        }
    except Exception as e:
        health_results["backend_services"]["response_formatter"] = {
            "status": "unhealthy",
            "details": f"Service error: {str(e)}"
        }
        unhealthy_count += 1
    
    # Determine overall status
    if unhealthy_count == 0:
        health_results["overall_status"] = "healthy"
    elif unhealthy_count <= 2:
        health_results["overall_status"] = "degraded"
    else:
        health_results["overall_status"] = "unhealthy"
    
    # Add summary
    total_services = len(MCP_SERVICES) + len(backend_services)
    healthy_services = total_services - unhealthy_count
    
    health_results["summary"] = {
        "total_services": total_services,
        "healthy_services": healthy_services,
        "unhealthy_services": unhealthy_count,
        "health_percentage": round((healthy_services / total_services) * 100, 2)
    }
    
    log.info("System health check completed", 
             overall_status=health_results["overall_status"],
             healthy_services=healthy_services,
             total_services=total_services)
    
    return health_results

@router.get("/services/status")
async def get_services_status(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Get detailed status of all MCP services"""
    services_status = {}
    
    for service_name, base_url in MCP_SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{base_url}/status", timeout=3.0)
                if response.status_code == 200:
                    services_status[service_name] = {
                        "status": "online",
                        "data": response.json()
                    }
                else:
                    services_status[service_name] = {
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    }
        except Exception as e:
            services_status[service_name] = {
                "status": "offline",
                "error": str(e)
            }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_status
    }

@router.post("/test/connectivity")
async def test_service_connectivity(
    service_name: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Test connectivity to a specific MCP service"""
    if service_name not in MCP_SERVICES:
        raise HTTPException(400, f"Unknown service: {service_name}")
    
    base_url = MCP_SERVICES[service_name]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test basic connectivity
            start_time = datetime.utcnow()
            response = await client.get(f"{base_url}/health", timeout=10.0)
            end_time = datetime.utcnow()
            
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "service": service_name,
                "url": base_url,
                "status": "connected" if response.status_code == 200 else "error",
                "response_time": response_time,
                "http_status": response.status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        return {
            "service": service_name,
            "url": base_url,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
