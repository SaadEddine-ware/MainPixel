from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.repositories.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_name = Column(String(100), default="system")
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<AuditLog {self.action} {self.entity_type}#{self.entity_id}>"
