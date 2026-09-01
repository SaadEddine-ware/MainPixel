from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from app.repositories.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    matiere_id = Column(Integer, ForeignKey("matieres.id", ondelete="CASCADE"), nullable=False)
    classe_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    semester = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    coefficient = Column(Float, default=1.0)
    date = Column(String(20), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Assignment {self.title}>"
