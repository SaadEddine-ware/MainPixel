from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.repositories.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    matiere_id = Column(Integer, ForeignKey("matieres.id", ondelete="CASCADE"), nullable=False)
    semester = Column(Integer, nullable=False)
    valeur = Column(Float, nullable=False)

    student = relationship("Student", back_populates="student_notes")
    matiere = relationship("Matiere")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("student_id", "matiere_id", "semester", name="uq_note"),
    )

    def __repr__(self):
        return f"<Note {self.valeur} student#{self.student_id} matiere#{self.matiere_id} S{self.semester}>"
