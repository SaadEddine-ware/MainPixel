from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.models.subject import Subject
from app.utils.curriculum import MOROCCAN_CURRICULUM

router = APIRouter()


@router.post("/seed-curriculum")
async def seed_curriculum(school_id: UUID, level: str = "middle", db: AsyncSession = Depends(get_db)):
    subjects_data = MOROCCAN_CURRICULUM.get(level)
    if not subjects_data:
        return {"error": f"Level '{level}' not found. Available: {list(MOROCCAN_CURRICULUM.keys())}"}

    created = []
    for s in subjects_data:
        existing = await db.execute(
            select(Subject).where(Subject.school_id == school_id, Subject.code == s["code"])
        )
        if not existing.scalar_one_or_none():
            obj = Subject(
                school_id=school_id,
                name=s["name"],
                code=s["code"],
                coefficient=s["coefficient"],
                level=level,
            )
            db.add(obj)
            created.append(s["name"])

    await db.commit()
    return {"level": level, "created": created, "count": len(created)}


@router.get("/curriculum")
async def get_curriculum():
    return MOROCCAN_CURRICULUM
