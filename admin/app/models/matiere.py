from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.repositories.database import Base


class Matiere(Base):
    __tablename__ = "matieres"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    coefficient = Column(Float, default=1.0, nullable=False)
    level_key = Column(String(50), nullable=False)
    year_name = Column(String(50))
    branch = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Matiere {self.name} (coef={self.coefficient})>"
