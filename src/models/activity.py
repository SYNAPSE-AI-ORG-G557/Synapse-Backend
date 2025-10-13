from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.base_class import Base

class ToolActivity(Base):
    __tablename__ = "tool_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # file_operation, web_search, email, calendar, etc.
    action = Column(String(100), nullable=False)  # upload, download, delete, send, create, etc.
    details = Column(Text)  # Additional details about the activity
    status = Column(String(20), default="success")  # success, error, pending
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship to user
    user = relationship("User", back_populates="tool_activities")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "action": self.action,
            "details": self.details,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
