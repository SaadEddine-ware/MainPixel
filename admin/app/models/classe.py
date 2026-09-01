from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.repositories.database import Base


class Classe(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)
    level_key = Column(String(50), nullable=False)
    level_name = Column(String(100), nullable=False)
    year_name = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    branch = Column(String(100), default="")
    academic_year = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    students = relationship("Student", back_populates="classe",
                            cascade="all, delete-orphan",
                            order_by="Student.sort_order")

    __table_args__ = (
        UniqueConstraint("level_key", "year_name", "name", "branch", name="uq_class"),
    )

    @property
    def student_count(self):
        return len(self.students) if self.students else 0

    def __repr__(self):
        return f"<Classe {self.name} ({self.level_name}/{self.year_name})>"
