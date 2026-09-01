from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.repositories.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    code_massar = Column(String(50), unique=True, index=True)
    full_name = Column(String(200), nullable=False)
    birth_date = Column(String(20))
    sexe = Column(String(10))
    address = Column(String(300))
    father_name = Column(String(200))
    mother_name = Column(String(200))
    comment = Column(String(500))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    classe = relationship("Classe", back_populates="students")
    student_notes = relationship("Note", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student {self.full_name} ({self.code_massar})>"
