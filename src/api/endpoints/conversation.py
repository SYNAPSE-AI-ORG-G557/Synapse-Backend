import uuid
import io
import csv
from typing import Annotated, List, Union

from fastapi import (
    APIRouter,
    Depends,
    status,
    Request,
    HTTPException,
    Query,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from src.schemas.conversation import (
    MessageCreate,
    MessagePublic,
    ConversationWithMessages,
    ConversationUpdate,
)
from pydantic import BaseModel
from src.schemas.job import JobCreate
from src.db.database import get_db_session
from src.core.celery_app import celery_app
from src.core.dependencies import get_current_active_user
from src.core.redis_client import redis_client
from src.db import models
from src.crud import conversation_crud
from src.services.real.db_service import RealDatabaseService
from src.services.real.redis_service import RealRedisService
from src.services.mcp_tools_service import mcp_tools_service
from src.websockets.manager import connection_manager
import logging

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
def get_redis() -> redis.Redis:
    """Dependency to get the Redis client instance."""
    return redis_client


def get_redis_service(
    client: Annotated[redis.Redis, Depends(get_redis)]
) -> RealRedisService:
    """Dependency to get an instance of the Redis service."""
    return RealRedisService(client)


# =============================================================================
# GET all conversations for the current user
# =============================================================================
@router.get(
    "/conversations/",
    response_model=List[ConversationWithMessages],
    summary="Get all conversations for the current user",
)
async def get_user_conversations(
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Retrieve all conversations and their associated messages for the current user.
    """
    stmt = (
        select(models.Conversation)
        .where(models.Conversation.user_id == current_user.uuid)
        .options(selectinload(models.Conversation.messages))
        .order_by(models.Conversation.updated_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# =============================================================================
# POST a new message and trigger AI response
# =============================================================================
@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Post a message and trigger AI response",
)
async def post_message(
    request: Request,
    conversation_id: uuid.UUID,
    message_in: MessageCreate,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    redis_service: Annotated[RealRedisService, Depends(get_redis_service)],
    current_user: Annotated[models.User, Depends(get_current_active_user)],
):
    """
    Orchestrates a full conversational turn:
    saves the message, creates a ProcessingJob, and dispatches it to workers.
    """
    db_service = RealDatabaseService(db_session)

    # Ensure the conversation exists
    await conversation_crud.conversation.get_or_create(
        db=db_session,
        user_id=current_user.uuid,
        conversation_id=conversation_id,
    )

    # Count messages before adding the new one
    message_count_before_add = await db_service.get_conversation_message_count(
        conversation_id
    )

    # Save user message
    created_message = await db_service.add_chat_message(
        user_id=current_user.uuid,
        conversation_id=conversation_id,
        role="user",
        content=message_in.content,
    )

    # Handle different chat modes
    if message_in.chat_mode == "tools":
        # Tools mode: Use MCP tools service
        try:
            logging.info(f"Processing tools mode query: {message_in.content}")
            tools_response = await mcp_tools_service.process_tools_query(
                query=message_in.content,
                user_id=str(current_user.uuid)
            )
            
            # Save assistant response
            assistant_message = await db_service.add_chat_message(
                user_id=current_user.uuid,
                conversation_id=conversation_id,
                role="assistant",
                content=tools_response,
            )
            
            # Send response via WebSocket
            await connection_manager.send_personal_message(
                message={
                    "type": "final_answer",
                    "content": tools_response,
                    "conversation_id": str(conversation_id),
                    "mode": "tools"
                },
                client_id=str(current_user.uuid)
            )
            
            return created_message
            
        except Exception as e:
            logging.error(f"Error in tools mode: {e}")
            error_response = f"❌ Error processing tools request: {str(e)}"
            
            # Save error response
            await db_service.add_chat_message(
                user_id=current_user.uuid,
                conversation_id=conversation_id,
                role="assistant",
                content=error_response,
            )
            
            # Send error via WebSocket
            await connection_manager.send_personal_message(
                message={
                    "type": "final_answer",
                    "content": error_response,
                    "conversation_id": str(conversation_id),
                    "mode": "tools"
                },
                client_id=str(current_user.uuid)
            )
            
            return created_message
    
    elif message_in.chat_mode == "both":
        # Both mode: Use both tools and personalization
        try:
            # First try tools
            tools_response = await mcp_tools_service.process_tools_query(
                query=message_in.content,
                user_id=str(current_user.uuid)
            )
            
            # If tools executed successfully, use that response
            if not tools_response.startswith("❌"):
                # Save assistant response
                assistant_message = await db_service.add_chat_message(
                    user_id=current_user.uuid,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=tools_response,
                )
                
                # Send response via WebSocket
                await connection_manager.send_personal_message(
                    message={
                        "type": "final_answer",
                        "content": tools_response,
                        "conversation_id": str(conversation_id),
                        "mode": "both"
                    },
                    client_id=str(current_user.uuid)
                )
                
                return created_message
        except Exception as e:
            logging.warning(f"Tools mode failed in 'both' mode, falling back to personalization: {e}")
        
        # Fall through to personalization if tools failed or no tools were needed
        pass
    
    # Personalization mode (default) or fallback from "both" mode
    # If first message → trigger title generation
    if message_count_before_add == 0:
        celery_app.send_task(
            "generate_title_task",
            args=[str(conversation_id), message_in.content],
            queue="cpu_heavy",
        )

    # Add message to Redis history
    await redis_service.add_message_to_history(
        conversation_id=conversation_id,
        message={"role": "user", "content": message_in.content},
    )

    # Create AI processing job
    job_id = uuid.uuid4()
    job_payload = JobCreate(
        user_id=current_user.uuid,
        conversation_id=conversation_id,
        input_type="text",
        input_data=message_in.content,
        is_personalization_enabled=message_in.is_personalization_enabled,
    )
    await db_service.create_job(job_id=job_id, job_data=job_payload)

    celery_app.send_task(
        "route_input_task",
        args=[
            str(job_id),
            str(current_user.uuid),
            job_payload.model_dump(),
            str(conversation_id),
            message_in.is_personalization_enabled,
        ],
        queue="cpu_light",
    )

    # Summarization trigger for long conversations
    SUMMARIZATION_THRESHOLD = 10
    if (message_count_before_add + 1) % SUMMARIZATION_THRESHOLD == 0:
        celery_app.send_task(
            "summarize_conversation_task",
            args=[str(conversation_id), str(current_user.uuid)],
            queue="cpu_heavy",
        )

    return created_message


# =============================================================================
# PATCH to rename a conversation
# =============================================================================
@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationWithMessages,
    summary="Rename a conversation",
)
async def rename_conversation(
    conversation_id: uuid.UUID,
    conversation_in: ConversationUpdate,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    stmt = select(models.Conversation).where(
        models.Conversation.uuid == conversation_id,
        models.Conversation.user_id == current_user.uuid,
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you do not have permission to edit it.",
        )

    conversation.title = conversation_in.title
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


# =============================================================================
# DELETE a conversation
# =============================================================================
@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    stmt = select(models.Conversation).where(
        models.Conversation.uuid == conversation_id,
        models.Conversation.user_id == current_user.uuid,
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you do not have permission to delete it.",
        )

    await session.delete(conversation)
    await session.commit()
    return None


# =============================================================================
# EXPORT a conversation (Markdown, CSV, or PDF)
# =============================================================================
@router.get(
    "/conversations/{conversation_id}/export",
    summary="Export a conversation",
)
async def export_conversation(
    conversation_id: uuid.UUID,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    format: Union[str, None] = Query(default="md", enum=["md", "csv", "pdf"]),
):
    """
    Export a conversation to Markdown (.md), CSV (.csv), or PDF (.pdf).
    """
    print(f"Export request: conversation_id={conversation_id}, user_id={current_user.uuid}, format={format}")
    stmt = (
        select(models.Conversation)
        .where(
            models.Conversation.uuid == conversation_id,
            models.Conversation.user_id == current_user.uuid,
        )
        .options(selectinload(models.Conversation.messages))
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    file_name = f"{conversation.title.replace(' ', '_')}_{conversation.uuid}.{format}"
    headers = {"Content-Disposition": f'attachment; filename="{file_name}"'}

    # --- Markdown Export ---
    if format == "md":
        content = f"# {conversation.title}\n\n"
        for msg in conversation.messages:
            content += f"**{msg.role.capitalize()}**:\n{msg.content}\n\n---\n\n"
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="text/markdown",
            headers=headers,
        )

    # --- CSV Export ---
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["role", "content", "created_at"])
        for msg in conversation.messages:
            writer.writerow([msg.role, msg.content, msg.created_at.isoformat()])
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers=headers,
        )

    # --- PDF Export ---
    if format == "pdf":
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.colors import HexColor, black, darkblue, darkgreen
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="PDF generation library (reportlab) is not installed."
            )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Custom styles for better formatting
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=HexColor('#0ea5e9'),  # Cyan color
            fontName='Helvetica-Bold'
        )
        
        # User message style
        user_style = ParagraphStyle(
            'UserMessage',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            leftIndent=20,
            rightIndent=20,
            borderColor=HexColor('#0ea5e9'),
            borderWidth=1,
            borderPadding=10,
            backColor=HexColor('#f0f9ff'),
            fontName='Helvetica'
        )
        
        # AI message style
        ai_style = ParagraphStyle(
            'AIMessage',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            leftIndent=20,
            rightIndent=20,
            borderColor=HexColor('#8b5cf6'),
            borderWidth=1,
            borderPadding=10,
            backColor=HexColor('#faf5ff'),
            fontName='Helvetica'
        )
        
        # Role header style
        role_style = ParagraphStyle(
            'RoleHeader',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=6,
            textColor=HexColor('#374151'),
            fontName='Helvetica-Bold'
        )

        story = []
        
        # Add title
        story.append(Paragraph(conversation.title, title_style))
        story.append(Spacer(1, 20))
        
        # Add metadata
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=20,
            textColor=HexColor('#6b7280'),
            alignment=TA_CENTER
        )
        story.append(Paragraph(f"Exported on: {conversation.updated_at.strftime('%B %d, %Y at %I:%M %p')}", metadata_style))
        story.append(Spacer(1, 20))

        # Add messages
        for i, msg in enumerate(conversation.messages):
            # Add role header
            role_text = "You" if msg.role == "user" else "Synapse AI"
            story.append(Paragraph(role_text, role_style))
            
            # Add message content with proper escaping
            content = msg.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            content = content.replace("\n", "<br/>")
            
            # Choose style based on role
            message_style = user_style if msg.role == "user" else ai_style
            story.append(Paragraph(content, message_style))
            
            # Add timestamp
            timestamp_style = ParagraphStyle(
                'Timestamp',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=15,
                textColor=HexColor('#9ca3af'),
                alignment=TA_LEFT
            )
            story.append(Paragraph(f"<i>{msg.created_at.strftime('%I:%M %p')}</i>", timestamp_style))
            
            # Add page break every 10 messages to prevent overly long pages
            if (i + 1) % 10 == 0 and i < len(conversation.messages) - 1:
                story.append(PageBreak())

        try:
            doc.build(story)
            buffer.seek(0)
            return StreamingResponse(
                buffer, 
                media_type="application/pdf", 
                headers=headers
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate PDF: {str(e)}"
            )

    raise HTTPException(status_code=400, detail="Invalid format specified.")


# =============================================================================
# SHARING SCHEMAS
# =============================================================================
class ShareCreate(BaseModel):
    share_token: str


class SharedConversation(BaseModel):
    uuid: str
    title: str
    messages: List[MessagePublic]
    shared_at: str
    updated_at: str


# =============================================================================
# POST to create a shareable link for a conversation
# =============================================================================
@router.post(
    "/conversations/{conversation_id}/share",
    response_model=dict,
    summary="Create a shareable link for a conversation",
)
async def create_share_link(
    conversation_id: uuid.UUID,
    share_data: ShareCreate,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Create a shareable link for a conversation by storing the share token.
    """
    # Verify the conversation exists and belongs to the user
    stmt = select(models.Conversation).where(
        models.Conversation.uuid == conversation_id,
        models.Conversation.user_id == current_user.uuid,
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you do not have permission to share it.",
        )

    # Store the share token in Redis with expiration (30 days)
    redis_service = RealRedisService(redis_client)
    share_key = f"share:{share_data.share_token}"
    share_data_dict = {
        "conversation_id": str(conversation_id),
        "user_id": str(current_user.uuid),
        "created_at": str(uuid.uuid4().time_low),  # Simple timestamp
    }
    
    await redis_service.client.hset(share_key, mapping=share_data_dict)
    await redis_service.client.expire(share_key, 30 * 24 * 60 * 60)  # 30 days

    return {
        "share_token": share_data.share_token,
        "share_url": f"/shared/{share_data.share_token}",
        "expires_in_days": 30
    }


# =============================================================================
# GET to retrieve a shared conversation (public access)
# =============================================================================
@router.get(
    "/shared/{share_token}",
    response_model=SharedConversation,
    summary="Get a shared conversation by token",
)
async def get_shared_conversation(
    share_token: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Retrieve a shared conversation using the share token (public access).
    """
    # Get share data from Redis
    redis_service = RealRedisService(redis_client)
    share_key = f"share:{share_token}"
    share_data = await redis_service.client.hgetall(share_key)
    
    if not share_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared conversation not found or link has expired.",
        )

    conversation_id = share_data.get(b"conversation_id", b"").decode()
    if not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid share token.",
        )

    # Get the conversation with messages
    stmt = (
        select(models.Conversation)
        .where(models.Conversation.uuid == conversation_id)
        .options(selectinload(models.Conversation.messages))
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or has been deleted.",
        )

    # Convert messages to public format
    messages = []
    for msg in conversation.messages:
        messages.append(MessagePublic(
            uuid=str(msg.uuid),
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
            conversation_id=str(msg.conversation_id)
        ))

    return SharedConversation(
        uuid=str(conversation.uuid),
        title=conversation.title,
        messages=messages,
        shared_at=share_data.get(b"created_at", b"").decode(),
        updated_at=conversation.updated_at.isoformat()
    )


# =============================================================================
# DELETE to revoke a share link
# =============================================================================
@router.delete(
    "/conversations/{conversation_id}/share",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a share link for a conversation",
)
async def revoke_share_link(
    conversation_id: uuid.UUID,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    share_token: str = Query(..., description="The share token to revoke"),
):
    """
    Revoke a share link by deleting the share token from Redis.
    """
    # Verify the conversation exists and belongs to the user
    stmt = select(models.Conversation).where(
        models.Conversation.uuid == conversation_id,
        models.Conversation.user_id == current_user.uuid,
    )
    result = await session.execute(stmt)
    conversation = result.scalars().first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you do not have permission to modify it.",
        )

    # Delete the share token from Redis
    redis_service = RealRedisService(redis_client)
    share_key = f"share:{share_token}"
    await redis_service.client.delete(share_key)

    return None