# Architecture — MainPixel

This document describes the system architecture, design decisions, and data flow patterns for MainPixel.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Style](#architecture-style)
- [Multi-Tenancy](#multi-tenancy)
- [Authentication & Authorization](#authentication--authorization)
- [Data Flow](#data-flow)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Database Design](#database-design)
- [Event System](#event-system)
- [Security Model](#security-model)
- [Caching Strategy](#caching-strategy)
- [File Storage](#file-storage)
- [Design Decisions](#design-decisions)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Users                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Admin   │  │ Teacher  │  │  Parent  │  │ Student  │   │
│  │ (browser)│  │ (browser)│  │ (browser)│  │ (browser)│   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │         │
│       └──────────────┴──────────────┴──────────────┘         │
│                          │ HTTPS                            │
│                          ▼                                  │
│               ┌─────────────────────┐                       │
│               │   React Frontend    │                       │
│               │  (Vite + TypeScript)│                       │
│               └──────────┬──────────┘                       │
│                          │ REST API calls                   │
│                          ▼                                  │
│               ┌─────────────────────┐                       │
│               │  FastAPI Backend    │                       │
│               │  (async Python)     │                       │
│               └──┬──────────┬───────┘                       │
│                  │          │                               │
│          ┌───────▼──┐  ┌───▼────────┐                      │
│          │PostgreSQL│  │   Redis    │                      │
│          │  (data)  │  │(cache/queue)│                      │
│          └──────────┘  └────────────┘                      │
│                                                             │
│               ┌─────────────────────┐                       │
│               │   SMTP / SMS API    │ ← notifications       │
│               └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Style

MainPixel uses a **modular monolith** architecture:

- **Single deployable unit**: One FastAPI application, one database, one Redis instance
- **Modular code organization**: Separate routers, services, models, and schemas per feature
- **Service layer**: Business logic lives in `services/`, not in routers (keeps routes thin)
- **Shared foundation**: Auth, tenancy, and event system are cross-cutting concerns used by all modules

### Why not microservices?

For a school management SaaS with a small team:
- Microservices add operational complexity (service discovery, distributed tracing, inter-service auth)
- The modules are tightly coupled (grades depend on students, attendance depends on timetable)
- A well-structured monolith can be split into services later if needed
- Single database transaction across modules is simpler in a monolith

---

## Multi-Tenancy

### Strategy: Shared database, shared schema, `school_id` column

Every table (except `schools` itself) includes a mandatory `school_id` foreign key. This is the cornerstone of data isolation.

```
┌─────────────────────────────────────────────────┐
│                 PostgreSQL                       │
│                                                  │
│  schools:                                        │
│  ┌─────────────────────────────────────────────┐ │
│  │ id (UUID PK)                                │ │
│  │ name                                        │ │
│  │ slug (unique)                               │ │
│  │ plan (free/standard/premium)                │ │
│  │ levels_config (JSON)                        │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  Every other table:                              │
│  ┌─────────────────────────────────────────────┐ │
│  │ id (UUID PK)                                │ │
│  │ school_id (FK → schools.id)  ← MANDATORY   │ │
│  │ ...other columns...                         │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Enforcement Layers

1. **Middleware (automatic)**: Every authenticated request has `school_id` extracted from JWT and injected into the database session. Routers don't need to manually add this filter.

2. **ORM-level (safety net)**: Base model class includes a `school_id` column with a default. Query helpers always filter by `school_id`.

3. **Service layer (explicit)**: Services accept `school_id` as a parameter and pass it to all queries.

4. **Tests (verification)**: Automated IDOR tests verify that a user from School A cannot access School B's data even by manipulating IDs.

### PostgreSQL Row-Level Security (RLS) — Recommended

For production, enable RLS on every table:

```sql
ALTER TABLE classes ENABLE ROW LEVEL SECURITY;

CREATE POLICY school_isolation ON classes
    USING (school_id = current_setting('app.current_school_id')::uuid);
```

The backend sets this session variable from the JWT on every request:

```python
await session.execute(text("SET app.current_school_id = :school_id"), {"school_id": str(school_id)})
```

This provides a database-level safety net even if a bug bypasses the ORM filter.

---

## Authentication & Authorization

### JWT Token Structure

```json
{
  "sub": "user-uuid",
  "school_id": "school-uuid",
  "role": "school_admin",
  "exp": 1234567890,
  "iat": 1234567800
}
```

### Token Lifecycle

```
User Login
    │
    ▼
POST /auth/login
    │
    ├── Invalid credentials → 401
    │
    ├── Valid → Returns:
    │   ├── access_token (30 min TTL)
    │   └── refresh_token (7 day TTL)
    │
    ▼
Client stores tokens (httpOnly cookie or memory)
    │
    ▼
Every API request includes: Authorization: Bearer <access_token>
    │
    ├── Token expired → 401 → Client uses refresh_token
    │
    ├── Token valid → Proceed to router
    │
    ▼
Tenant Middleware
    │
    ├── Extract school_id from JWT
    │   ├── school_id missing → Reject
    │   └── school_id present → SET on DB session
    │
    ▼
Role Middleware (per-route)
    │
    ├── Check user.role in allowed_roles
    │   ├── Not allowed → 403
    │   └── Allowed → Proceed to service
    │
    ▼
Service Layer
    │
    ├── All queries filter by school_id (automatic from session)
    │
    ▼
Response
```

### Rate Limiting

Applied to auth endpoints only:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /auth/login` | 5 attempts | 15 minutes per IP + email |
| `POST /auth/register` | 3 attempts | 1 hour per IP |
| `POST /auth/refresh` | 10 attempts | 15 minutes per IP |

Implementation: Redis-based sliding window counter.

---

## Data Flow

### Grade Entry (Teacher → Admin)

```
Teacher selects class + subject + assignment
    │
    ▼
Enters grades in grid UI
    │
    ▼
Frontend: POST /assignments/{id}/grades
  Body: { "grades": { "student-uuid": 15.5, ... } }
    │
    ▼
Backend router: assignments.py
    │
    ├── Validate: user.role == teacher
    ├── Validate: assignment exists in school
    ├── Validate: grades within 0-20 range
    │
    ▼
Service: assignment_service.save_grades()
    │
    ├── Upsert assignment_grades records
    ├── Emit event: "grades_published"
    │
    ▼
Event handler: notification_service
    │
    ├── Create in-app notification for each student
    ├── Queue email notification (async)
    │
    ▼
Response: 200 OK
```

### Attendance Recording (Teacher → Parent Notification)

```
Teacher: POST /attendance
  Body: {
    "classe_id": "...",
    "date": "2026-08-29",
    "period": "morning",
    "records": [
      { "student_id": "...", "status": "absent" },
      { "student_id": "...", "status": "present" },
      ...
    ]
  }
    │
    ▼
Backend: Bulk insert attendance_records
    │
    ├── Check: student has ≤ 3 unjustified absences
    │   ├── Exceeded → Emit "absence_threshold_exceeded" event
    │   └── Below → No action
    │
    ▼
Event handler: notification_service
    │
    ├── Find parent linked to student (via parent_student)
    ├── Create notification: "Your child was absent on [date]"
    ├── Queue email/SMS to parent
    │
    ▼
Response: 200 OK
```

### Admission → Student Auto-provisioning

```
Parent: POST /admissions/apply (public, CAPTCHA)
  Body: { "applicant_name": "...", "birth_date": "...", ... }
    │
    ▼
Backend: Create admission_applications record (status: submitted)
    │
    ▼
Admin: PATCH /admissions/{id}/status
  Body: { "status": "accepted" }
    │
    ▼
Single database transaction:
    │
    ├── 1. Create students record
    ├── 2. Link to class
    ├── 3. Find or create parent user account
    ├── 4. Create parent_student link
    ├── 5. Update admission status
    ├── 6. Emit "admission_accepted" event
    │
    ├── Any failure → Rollback everything
    │
    ▼
Event handler: notification_service
    │
    └── Send acceptance email to parent
```

---

## Backend Architecture

### Request Lifecycle

```
HTTP Request
    │
    ▼
FastAPI App
    │
    ├── Middleware (in order):
    │   ├── CORS
    │   ├── Request ID logging
    │   └── Rate limiting (auth endpoints only)
    │
    ├── Router (per module)
    │   │
    │   ├── Dependencies (injected):
    │   │   ├── get_db() → async session
    │   │   ├── get_current_user() → decode JWT, fetch user
    │   │   └── require_role(["admin", "teacher"]) → check role
    │   │
    │   ├── Schema validation (Pydantic)
    │   │
    │   └── Call service method
    │       │
    │       ├── Service uses session (school_id auto-filtered)
    │       ├── Business logic + validation
    │       ├── Emit events if needed
    │       │
    │       └── Return response model
    │
    ▼
JSON Response
```

### Module Structure

Each feature module follows the same pattern:

```
module/
├── router.py       # Route definitions + dependency injection
├── schemas.py      # Pydantic models (request/response)
├── service.py      # Business logic (pure functions, no HTTP)
└── models.py       # SQLAlchemy ORM models (shared across modules)
```

### Dependency Injection (FastAPI)

```python
# deps.py

async def get_db():
    async with AsyncSession(engine) as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_jwt(token)
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

### Router Example

```python
# routers/classes.py

router = APIRouter(prefix="/classes", tags=["classes"])

@router.get("/", response_model=list[ClasseResponse])
async def list_classes(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("school_admin", "teacher")),
):
    return await class_service.list_classes(db, user.school_id)

@router.post("/", response_model=ClasseResponse, status_code=201)
async def create_class(
    data: ClasseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("school_admin")),
):
    return await class_service.create_class(db, user.school_id, data)
```

---

## Frontend Architecture

### Routing

```
/login                              → Login page (public)
/
├── /admin                          → Admin layout (school_admin only)
│   ├── /dashboard                  → Overview stats
│   ├── /classes                    → Class management
│   │   └── /classes/:id/students   → Student list
│   ├── /subjects                   → Subject management
│   ├── /grades                     → Grade entry
│   ├── /assignments                → Assignment management
│   ├── /attendance                 → Attendance records
│   ├── /timetable                  → Schedule builder
│   ├── /invoices                   → Fee management
│   ├── /admissions                 → Application review
│   ├── /notifications              → Notification center
│   ├── /teachers                   → User management
│   ├── /config                     → School settings
│   └── /export                     → Reports
│
├── /teacher                        → Teacher layout
│   ├── /classes                    → View assigned classes
│   ├── /attendance                 → Record attendance
│   └── /assignments                → Grade assignments
│
├── /parent                         → Parent portal (read-only)
│   ├── /children                   → List children
│   └── /children/:id              → Child detail (grades, attendance, timetable)
│
└── /student                        → Student portal (read-only)
    ├── /grades                     → Own grades
    ├── /attendance                 → Own attendance
    └── /timetable                  → Own timetable
```

### State Management

- **Server state**: React Query (TanStack Query) for API data caching
- **Auth state**: React Context (JWT tokens, user info)
- **Form state**: React Hook Form (for complex forms like grade entry)
- **UI state**: Local component state (modals, toggles)

### API Client

```typescript
// api/client.ts

import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
});

// Auto-attach access token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        const { data } = await axios.post("/api/auth/refresh", { refresh_token: refresh });
        localStorage.setItem("access_token", data.access_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return api(error.config);
      }
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Component Architecture

```
App
├── AuthProvider (Context)
│   ├── PublicRoute → Login
│   └── PrivateRoute → Layout
│       ├── Sidebar (role-based menu)
│       ├── Header (user info, notifications bell)
│       └── PageContent (React Query + API calls)
│           ├── DataTable (reusable sortable/filterable table)
│           ├── GradeGrid (reusable grade entry grid)
│           ├── Modal (reusable dialog)
│           ├── SearchInput (debounced search)
│           └── ...
```

---

## Database Design

### Entity Relationship Summary

```
schools ─────────────────────────────────────────────────────────┐
    │                                                             │
    ├── users ────────────────────────────────────────────────┐  │
    │   └── parent_student ──┐                                │  │
    │                        └── students ──────────────────┐ │  │
    │                                                     │ │  │
    ├── classes ──────────────────────────────────────────┘ │  │
    │   └── students ───────────────────────────────────────┘  │
    │                                                          │
    ├── matieres ────────────────────────────────────────────┐ │
    │                                                      │ │ │
    ├── notes ── (student_id, matiere_id) ─────────────────┘ │ │
    │                                                        │ │
    ├── assignments ── (classe_id, matiere_id) ──────────────┘ │
    │   └── assignment_grades ── (student_id) ────────────────┘
    │
    ├── attendance_records ── (student_id, classe_id)
    ├── timetable_slots ── (classe_id, matiere_id, teacher_id)
    ├── fee_plans
    ├── invoices ── (student_id, fee_plan_id)
    ├── admission_applications
    ├── notifications ── (recipient_user_id)
    └── audit_logs
```

Full schema: [DATABASE.md](./DATABASE.md)

---

## Event System

### Purpose

Decouple side effects (notifications, logging) from core operations (grade entry, attendance recording).

### Architecture

```python
# events.py

from typing import Callable, Any
from dataclasses import dataclass

@dataclass
class Event:
    type: str
    school_id: str
    payload: dict

_handlers: dict[str, list[Callable]] = {}

def on(event_type: str, handler: Callable):
    _handlers.setdefault(event_type, []).append(handler)

def emit(event: Event):
    for handler in _handlers.get(event.type, []):
        handler(event)

# Register handlers
def setup_events():
    from app.services import notification_service

    on("grades_published", notification_service.handle_grades_published)
    on("absence_recorded", notification_service.handle_absence_recorded)
    on("absence_threshold_exceeded", notification_service.handle_absence_alert)
    on("invoice_overdue", notification_service.handle_invoice_overdue)
    on("admission_accepted", notification_service.handle_admission_accepted)
```

### Event Types

| Event | Trigger | Handler |
|-------|---------|---------|
| `grades_published` | Assignment grades saved | Notify students/parents |
| `absence_recorded` | Attendance marked absent | Check threshold |
| `absence_threshold_exceeded` | Student crosses absence limit | Alert parent |
| `invoice_overdue` | Invoice past due date | Notify parent + admin |
| `admission_accepted` | Application accepted | Welcome email |
| `admission_rejected` | Application rejected | Rejection email |

### Async Processing

For MVP: handlers execute synchronously (in the same request).
For production: handlers push to Redis queue, a background worker processes them.

---

## Security Model

### Data Isolation

1. **JWT contains `school_id`**: Every authenticated request carries the school identity
2. **Middleware extracts `school_id`**: Injected into the database session
3. **All queries filter by `school_id`**: Service layer enforces this
4. **RLS in PostgreSQL**: Database-level safety net
5. **IDOR tests**: Automated tests verify cross-school access is blocked

### Password Security

- **Hashing**: bcrypt with work factor 12
- **Never store plaintext**: Only hashed passwords
- **Salt**: Generated per-password (bcrypt handles this)

### Input Validation

- **Pydantic schemas**: Strict type checking on all inputs
- **SQL injection**: Impossible with SQLAlchemy ORM (parameterized queries)
- **XSS**: React escapes output by default; CSP headers recommended
- **CSRF**: SameSite cookies + CSRF tokens for state-changing operations

### Audit Trail

Every significant action is logged in `audit_logs`:

```python
# In service layer
await audit_log.create(
    db=db,
    school_id=school_id,
    user_id=user.id,
    action="create",
    entity_type="student",
    entity_id=student.id,
    details=f"Added student {student.full_name}",
)
```

---

## Caching Strategy

### Redis Usage

| Use Case | TTL | Pattern |
|----------|-----|---------|
| Dashboard statistics | 5 min | `dashboard:{school_id}:{period}` |
| User sessions / tokens | 30 min | `session:{user_id}` |
| Rate limiting counters | 15 min | `ratelimit:{endpoint}:{ip}:{email}` |
| Notification queue | — | `queue:notifications` (list) |

### Cache Invalidation

- **Grade changes**: Invalidate dashboard cache for that school
- **Attendance changes**: Invalidate attendance stats cache
- **Config changes**: Invalidate subject/class caches

### Future Optimization

- Cache heavy aggregation queries (dashboard, grade distribution)
- Use Redis pub/sub for real-time updates (WebSocket for live dashboard)

---

## File Storage

### Current (MVP)

Files stored on the local filesystem:

```
~/.mainpixel/data/{school_id}/uploads/
├── admission_documents/
│   ├── {uuid}_birth_certificate.pdf
│   └── {uuid}_photo.jpg
├── attendance_justifications/
│   └── {uuid}_medical_certificate.pdf
└── exports/
    ├── class_{id}_report.html
    └── student_{id}_certificate.pdf
```

### Future (Production)

Migrate to S3-compatible storage (MinIO self-hosted or AWS S3):
- Files stored with `{school_id}/{type}/{uuid}_{filename}` prefix
- Signed URLs for secure access
- CDN for exported reports

---

## Design Decisions

### 1. UUID vs Integer PKs

**Decision: UUIDs (v4)**

Pros:
- No ID guessing (security)
- Can generate client-side (offline support later)
- No collision across schools
- Safe for public URLs

Cons:
- 16 bytes vs 4 bytes (storage)
- No natural ordering (use `created_at` instead)
- Indexes slightly larger

### 2. Async SQLAlchemy

**Decision: Yes, async**

Pros:
- Non-blocking I/O during database queries
- Better concurrency under load
- FastAPI is async-native

Cons:
- Slightly more complex session management
- Some SQLAlchemy extensions don't support async yet

### 3. Alembic vs Auto-migration

**Decision: Alembic (explicit migrations)**

Pros:
- Version-controlled schema changes
- Rollback capability
- Team collaboration (merge migration files)
- Production-safe

### 4. Pydantic v2 vs v1

**Decision: Pydantic v2**

Pros:
- 5-50x faster validation
- Better type inference
- Native SQLAlchemy integration via `sqlmodel`
- stricter default behavior

### 5. Monolith vs Microservices

**Decision: Modular monolith**

(See [Architecture Style](#architecture-style) for rationale)

### 6. Frontend State Management

**Decision: React Query + Context (no Redux)**

Pros:
- React Query handles server state (cache, refetch, optimistic updates)
- Context handles auth state (simple, no external dependency)
- Less boilerplate than Redux
- Better TypeScript inference

---

## Scalability Considerations

### Current Capacity (Single Server)

- **Database**: PostgreSQL handles ~10,000 concurrent connections
- **API**: FastAPI handles ~10,000 req/s on a 4-core server
- **Cache**: Redis handles ~100,000 ops/s

### Growth Path

1. **Phase 1 (MVP)**: Single server, Docker Compose
2. **Phase 2 (Growth)**: Separate API + DB servers, add read replicas
3. **Phase 3 (Scale)**: Kubernetes, horizontal scaling, CDN for frontend

### Database Optimization

- Indexes on `school_id` + frequently queried columns
- Connection pooling via `asyncpg` pool
- Read replicas for dashboard queries
- Partitioning `audit_logs` and `attendance_records` by date (if > 1M rows)

---

## Monitoring & Observability

### Logging

Structured JSON logs via `structlog`:

```json
{
  "timestamp": "2026-08-29T10:30:00Z",
  "level": "info",
  "message": "Grade saved",
  "school_id": "abc-123",
  "user_id": "def-456",
  "student_id": "ghi-789",
  "assignment_id": "jkl-012",
  "request_id": "req-uuid"
}
```

### Metrics (Future)

- Prometheus metrics for request count, latency, error rate
- Grafana dashboards for monitoring

### Tracing (Future)

- OpenTelemetry for distributed tracing
- Jaeger for trace visualization
