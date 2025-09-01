import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.crud.base import CRUDBase
from src.db.models import Conversation
from src.schemas.user import UserCreate  # Placeholder, not used directly

class CRUDConversation(CRUDBase[Conversation, UserCreate, UserCreate]):
    async def get_or_create(
        self, 
        db: AsyncSession, 
        *, 
        user_id: uuid.UUID, 
        conversation_id: uuid.UUID
    ) -> Conversation:
        """
        Tries to get a conversation by its ID. If it doesn't exist, it creates a new one.
        """
        # First, try to get the existing conversation
        result = await db.execute(select(self.model).filter(self.model.uuid == conversation_id))
        instance = result.scalars().first()
        
        if instance:
            return instance
        
        # If it doesn't exist, create it with a default title
        new_conversation = Conversation(
            uuid=conversation_id,
            user_id=user_id,
            title=f"Conversation from {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        db.add(new_conversation)
        await db.commit()
        await db.refresh(new_conversation)
        return new_conversation

conversation = CRUDConversation(Conversation)