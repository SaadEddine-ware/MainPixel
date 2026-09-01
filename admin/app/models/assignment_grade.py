from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from app.repositories.database import Base


class AssignmentGrade(Base):
    __tablename__ = "assignment_grades"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    valeur = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_assignment_grade"),
    )

    def __repr__(self):
        return f"<AssignmentGrade {self.valeur}>"
