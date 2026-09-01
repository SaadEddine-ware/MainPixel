import asyncio
import uuid
from datetime import datetime, timezone
from app.core.database import engine, async_session, Base
from app.core.security import hash_password
from app.models.school import School
from app.models.user import User, UserRole


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        demo_school = School(
            id=uuid.uuid4(),
            name="École Demo MainPixel",
            slug="demo",
            address="123 Rue Example, Casablanca",
            phone="+212600000000",
            email="contact@demo.mainpixel.ma",
            is_active=True,
        )
        session.add(demo_school)
        await session.flush()

        super_admin = User(
            id=uuid.uuid4(),
            school_id=None,
            email="super@mainpixel.ma",
            hashed_password=hash_password("SuperAdmin123!"),
            first_name="Super",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        school_admin = User(
            id=uuid.uuid4(),
            school_id=demo_school.id,
            email="admin@demo.mainpixel.ma",
            hashed_password=hash_password("Admin123!"),
            first_name="Admin",
            last_name="École",
            role=UserRole.SCHOOL_ADMIN,
            is_active=True,
        )
        teacher = User(
            id=uuid.uuid4(),
            school_id=demo_school.id,
            email="teacher@demo.mainpixel.ma",
            hashed_password=hash_password("Teacher123!"),
            first_name="Mohammed",
            last_name="Alami",
            role=UserRole.TEACHER,
            is_active=True,
        )
        parent = User(
            id=uuid.uuid4(),
            school_id=demo_school.id,
            email="parent@demo.mainpixel.ma",
            hashed_password=hash_password("Parent123!"),
            first_name="Fatima",
            last_name="Benali",
            role=UserRole.PARENT,
            is_active=True,
        )
        student = User(
            id=uuid.uuid4(),
            school_id=demo_school.id,
            email="student@demo.mainpixel.ma",
            hashed_password=hash_password("Student123!"),
            first_name="Youssef",
            last_name="Benali",
            role=UserRole.STUDENT,
            is_active=True,
        )

        session.add_all([super_admin, school_admin, teacher, parent, student])
        await session.commit()
        print("Seed complete: 1 school, 5 users created.")


if __name__ == "__main__":
    asyncio.run(seed())
