# Create this new file at: Synapse-Backend/src/api/endpoints/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.websockets.manager import connection_manager
from src.schemas.websocket import WSClarificationResponse
from src.core.celery_app import celery_app

router = APIRouter()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await connection_manager.connect(client_id, websocket)
    try:
        while True:
            # Listen for incoming messages from the user
            data = await websocket.receive_json()
            
            # Validate and process the user's clarification response
            response = WSClarificationResponse.model_validate(data)
            
            print(f"Received clarification response for job {response.job_id} from {client_id}")

            # Dispatch a new Celery task to resume the workflow
            celery_app.send_task(
                "resume_with_clarification_task",
                # Note: The client_id is our user_id in this architecture
                args=[str(response.job_id), client_id, response.selected_option],
                queue='cpu_light'
            )

    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
    except Exception as e:
        print(f"Error in websocket for {client_id}: {e}")
        connection_manager.disconnect(client_id)