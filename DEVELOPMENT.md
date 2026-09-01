# Development Guide — MainPixel

Everything you need to set up a local development environment and contribute to the project.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Backend Development](#backend-development)
- [Frontend Development](#frontend-development)
- [Database](#database)
- [Testing](#testing)
- [Code Style](#code-style)
- [Git Workflow](#git-workflow)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend runtime |
| npm | 10+ | Package manager |
| Docker | 24+ | Database infrastructure |
| Docker Compose | v2 | Multi-container setup |
| Git | 2.40+ | Version control |

### Optional but recommended

| Tool | Purpose |
|------|---------|
| [pyenv](https://github.com/pyenv/pyenv) | Python version management |
| [nvm](https://github.com/nvm-sh/nvm) | Node version management |
| [pgAdmin](https://www.pgadmin.org/) | Database GUI (included in Docker) |
| [Redis Commander](https://github.com/joeferner/redis-commander) | Redis GUI |
| [DBeaver](https://dbeaver.io/) | Universal database GUI |

---

## Environment Setup

### 1. Clone the repository

```bash
git clone https://github.com/SaadEddine-ware/MainPixel.git
cd MainPixel
```

### 2. Create `.env` file

```bash
cp .env.example .env
```

Edit `.env` with your local settings:

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mainpixel
POSTGRES_USER=mainpixel
POSTGRES_PASSWORD=mainpixel_dev_password

# Redis
REDIS_URL=redis://localhost:6379/0

# Backend
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=postgresql+asyncpg://mainpixel:mainpixel_dev_password@localhost:5432/mainpixel
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:5173"]

# Frontend
VITE_API_URL=http://localhost:8000/api

# Email (optional for dev)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=changeme
```

### 3. Start infrastructure

```bash
docker compose up -d
```

This starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- pgAdmin on `http://localhost:5050` (admin@admin.com / admin)

### 4. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: .\venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 5. Frontend setup

```bash
cd frontend
npm install
```

### 6. Initialize database

```bash
cd backend
alembic upgrade head
python -m app.seed
```

### 7. Start development servers

Terminal 1 (Backend):
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

### 8. Verify

- Backend API docs: http://localhost:8000/docs
- Frontend app: http://localhost:5173
- pgAdmin: http://localhost:5050

---

## Backend Development

### Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   ├── env.py                  # Alembic config
│   └── script.py.mako          # Migration template
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings (pydantic-settings)
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models/                 # ORM models
│   ├── schemas/                # Pydantic schemas
│   ├── routers/                # API routes
│   ├── services/               # Business logic
│   ├── middleware/              # Custom middleware
│   ├── deps.py                 # Dependency injection
│   ├── security.py             # JWT + password hashing
│   ├── events.py               # Event system
│   └── seed.py                 # Seed script
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Production Docker build
└── .env.example                # Environment template
```

### Key Files

**`app/main.py`** — FastAPI application setup:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine
from app.routers import auth, classes, students, ...

app = FastAPI(title="MainPixel API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(classes.router, prefix="/api/classes", tags=["classes"])
# ...

@app.on_event("startup")
async def startup():
    # Initialize database, seed data, etc.
    pass

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
```

**`app/config.py`** — Environment-based settings:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"

settings = Settings()
```

**`app/deps.py`** — Dependency injection:

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.security import decode_jwt
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_db():
    async with AsyncSession(engine) as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_jwt(token)
    except Exception:
        raise HTTPException(401, "Invalid token")

    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "Invalid token")
    return user

def require_role(*roles: str):
    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker
```

### Adding a New Feature

1. **Create models** in `app/models/`:
   ```python
   # app/models/my_feature.py
   from sqlalchemy import Column, String, ForeignKey
   from app.database import Base

   class MyFeature(Base):
       __tablename__ = "my_features"
       id = Column(UUID, primary_key=True, default=uuid4)
       school_id = Column(UUID, ForeignKey("schools.id"), nullable=False)
       # ... other columns
   ```

2. **Create schemas** in `app/schemas/`:
   ```python
   # app/schemas/my_feature.py
   from pydantic import BaseModel
   from uuid import UUID

   class MyFeatureCreate(BaseModel):
       name: str

   class MyFeatureResponse(BaseModel):
       id: UUID
       name: str
       school_id: UUID

       class Config:
           from_attributes = True
   ```

3. **Create service** in `app/services/`:
   ```python
   # app/services/my_feature_service.py
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.models.my_feature import MyFeature

   async def create_feature(db: AsyncSession, school_id: UUID, data: MyFeatureCreate):
       feature = MyFeature(school_id=school_id, **data.model_dump())
       db.add(feature)
       await db.commit()
       return feature
   ```

4. **Create router** in `app/routers/`:
   ```python
   # app/routers/my_feature.py
   from fastapi import APIRouter, Depends
   from app.deps import get_db, get_current_user, require_role
   from app.models.user import User
   from app.schemas.my_feature import MyFeatureCreate, MyFeatureResponse

   router = APIRouter()

   @router.post("/", response_model=MyFeatureResponse, status_code=201)
   async def create(
       data: MyFeatureCreate,
       db: AsyncSession = Depends(get_db),
       user: User = Depends(require_role("school_admin")),
   ):
       return await create_feature(db, user.school_id, data)
   ```

5. **Include router** in `app/main.py`:
   ```python
   from app.routers import my_feature
   app.include_router(my_feature.router, prefix="/api/my-features", tags=["my-features"])
   ```

6. **Create migration**:
   ```bash
   alembic revision --autogenerate -m "add my_features table"
   alembic upgrade head
   ```

7. **Write tests** in `tests/`.

---

## Frontend Development

### Project Structure

```
frontend/
├── src/
│   ├── main.tsx                 # React entry point
│   ├── App.tsx                  # Router + layout
│   ├── api/                     # API client
│   │   └── client.ts            # Axios instance
│   ├── auth/                    # Auth context
│   │   ├── AuthContext.tsx
│   │   └── useAuth.ts
│   ├── types/                   # TypeScript types
│   │   └── index.ts
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── admin/               # Admin pages
│   │   ├── teacher/             # Teacher pages
│   │   ├── parent/              # Parent portal
│   │   └── student/             # Student portal
│   ├── components/              # Reusable components
│   │   ├── Layout.tsx
│   │   ├── DataTable.tsx
│   │   ├── GradeGrid.tsx
│   │   └── Modal.tsx
│   └── utils/                   # Helpers
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

### Key Technologies

| Library | Purpose |
|---------|---------|
| React 18 | UI framework |
| TypeScript 5 | Type safety |
| Vite | Build tool + dev server |
| React Router 6 | Client-side routing |
| TanStack Query | Server state management |
| Axios | HTTP client |
| TailwindCSS | Styling |
| React Hook Form | Form management |
| Zod | Schema validation |

### Adding a New Page

1. **Create the page component**:
   ```tsx
   // src/pages/admin/MyPage.tsx
   import { useQuery } from "@tanstack/react-query";
   import api from "../../api/client";

   export default function MyPage() {
     const { data, isLoading } = useQuery({
       queryKey: ["my-data"],
       queryFn: () => api.get("/my-features").then((r) => r.data),
     });

     if (isLoading) return <div>Loading...</div>;

     return (
       <div>
         <h1>My Page</h1>
         {/* Render data */}
       </div>
     );
   }
   ```

2. **Add route** in `App.tsx`:
   ```tsx
   import MyPage from "./pages/admin/MyPage";

   <Route path="/admin/my-page" element={
     <ProtectedRoute allowedRoles={["school_admin"]}>
       <Layout><MyPage /></Layout>
     </ProtectedRoute>
   } />
   ```

3. **Add navigation** in `Layout.tsx` sidebar.

---

## Database

### Connect to PostgreSQL

```bash
# Using psql CLI
psql -h localhost -p 5432 -U mainpixel -d mainpixel

# Using pgAdmin (browser)
# http://localhost:5050
# Email: admin@admin.com, Password: admin
```

### Useful Commands

```sql
-- List tables
\dt

-- Describe a table
\d students

-- Count students per class
SELECT c.name, COUNT(s.id) as student_count
FROM classes c
LEFT JOIN students s ON s.class_id = c.id
GROUP BY c.name;

-- Find classes by level
SELECT * FROM classes WHERE level_key = 'middle';

-- Check migration version
SELECT version_num FROM alembic_version;
```

### Create a Test School

```python
# In Python shell: python -c "..."
import asyncio
from app.database import get_session
from app.models.school import School
from app.models.user import User
from uuid import uuid4

async def create_test_school():
    async with get_session() as db:
        school = School(
            id=uuid4(),
            name="Test School",
            slug="test-school",
            plan="trial",
            levels_config={
                "levels": {"primary": "Primaire", "middle": "Collège"},
                "years_structure": {"primary": ["1", "2", "3"], "middle": ["1", "2", "3"]}
            }
        )
        db.add(school)
        await db.commit()

asyncio.run(create_test_school())
```

---

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_login_success

# Run with coverage
pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm run test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

### Test Structure

```
backend/tests/
├── conftest.py          # Shared fixtures (test DB, test client, etc.)
├── test_auth.py         # Auth endpoint tests
├── test_classes.py      # Class CRUD tests
├── test_students.py     # Student CRUD tests
├── test_grades.py       # Grade calculation tests
├── test_attendance.py   # Attendance tests
├── test_tenancy.py      # Multi-tenancy isolation tests (CRITICAL)
└── test_idor.py         # IDOR attack prevention tests
```

### Writing a Test

```python
# tests/test_classes.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_class(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/classes/",
        json={
            "level_key": "middle",
            "year_name": "3",
            "name": "3ème A",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "3ème A"
    assert "id" in data

@pytest.mark.asyncio
async def test_cross_school_access_forbidden(
    client: AsyncClient,
    school_a_headers: dict,
    school_b_class_id: str,
):
    """CRITICAL: Verify School A cannot access School B's data."""
    response = await client.get(
        f"/api/classes/{school_b_class_id}",
        headers=school_a_headers,
    )
    assert response.status_code in (403, 404)
```

---

## Code Style

### Python (Backend)

**Formatter:** `ruff format`
**Linter:** `ruff check`

```bash
# Format all files
ruff format .

# Lint all files
ruff check .

# Auto-fix lint issues
ruff check --fix .
```

**Rules:**
- Double quotes for strings
- Trailing commas in multi-line structures
- Type hints on all function signatures
- Docstrings on all public functions
- No unused imports

### TypeScript (Frontend)

**Linter:** `eslint`
**Formatter:** `prettier`

```bash
# Lint
npm run lint

# Format
npm run format
```

**Rules:**
- 2-space indentation
- Single quotes for strings
- Semicolons required
- No unused variables (error)
- Explicit return types on exported functions

---

## Git Workflow

### Branch Strategy

```
main          ← Production-ready code
├── develop   ← Integration branch
│   ├── feature/auth-system
│   ├── feature/class-management
│   └── feature/grade-entry
```

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add class creation endpoint
fix: correct grade average calculation
docs: update API documentation
test: add tenancy isolation tests
refactor: extract grade service logic
chore: update dependencies
```

### Pre-commit Hooks

Install pre-commit:

```bash
pip install pre-commit
pre-commit install
```

Hooks run automatically:
- `ruff check` (Python linting)
- `ruff format` (Python formatting)
- `eslint` (TypeScript linting)
- `prettier` (TypeScript formatting)

---

## Common Tasks

### Add a new migration

```bash
cd backend
alembic revision --autogenerate -m "description of change"
# Review the generated migration in alembic/versions/
alembic upgrade head
```

### Reset database

```bash
cd backend
alembic downgrade base
alembic upgrade head
python -m app.seed
```

### Seed Moroccan curriculum for a school

```python
from app.services.grade_service import seed_matieres
from app.database import get_session

async with get_session() as db:
    count = await seed_matieres(db, school_id="your-school-uuid")
    print(f"Seeded {count} subjects")
```

### Generate API client for frontend

```bash
cd frontend
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```

---

## Troubleshooting

### PostgreSQL connection refused

```bash
# Check if Docker container is running
docker compose ps

# Restart PostgreSQL
docker compose restart postgres

# Check logs
docker compose logs postgres
```

### Alembic migration conflicts

```bash
# If two migrations modify the same table
alembic merge -m "merge description" rev1 rev2
alembic upgrade head
```

### Port already in use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Frontend can't connect to backend

1. Check `VITE_API_URL` in `.env`
2. Check CORS settings in backend `config.py`
3. Verify backend is running: `curl http://localhost:8000/docs`

### Redis connection refused

```bash
# Check Redis container
docker compose ps redis

# Restart Redis
docker compose restart redis

# Test connection
redis-cli ping
```
