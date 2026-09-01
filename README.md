# MainPixel — School Management Platform

A multi-tenant SaaS platform for managing Moroccan schools: students, grades, attendance, timetables, invoicing, admissions, and parent/student portals.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Features](#features)
- [Roles & Permissions](#roles--permissions)
- [API Overview](#api-overview)
- [Database](#database)
- [Deployment](#deployment)
- [Legal Requirements](#legal-requirements)
- [Contributing](#contributing)

---

## Overview

MainPixel is a web-based school management system designed for the Moroccan education system. It supports multi-tenancy (multiple schools on one deployment), role-based access control, and covers the full lifecycle from student admission to graduation.

### Key Design Principles

- **Multi-tenancy first**: Every table has a `school_id`. Data isolation is enforced at the ORM/query level. No cross-school data leaks.
- **Moroccan curriculum native**: Pre-seeded subjects and coefficients for Primaire, Collège, and Lycée (all branches).
- **Offline-capable future**: The REST API is designed to support a mobile app with offline-first sync later.
- **Event-driven notifications**: Grades, attendance, and invoices emit events that trigger in-app/email/SMS notifications.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| **Database** | PostgreSQL 16 |
| **Cache / Queue** | Redis 7 |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS, React Router |
| **Auth** | JWT (access + refresh tokens), bcrypt password hashing |
| **Infrastructure** | Docker, Docker Compose |
| **Testing** | pytest, pytest-asyncio, httpx (API tests) |
| **CI/CD** | GitHub Actions (planned) |

---

## Project Structure

```
MainPixel/
├── legacy/                          # Old Python desktop apps (archived)
│   ├── admin/                       #   Original admin desktop app
│   └── teacher/                     #   Original teacher desktop app
│
├── backend/                         # FastAPI REST API
│   ├── alembic/                     #   Database migrations
│   │   ├── versions/                #   Migration scripts
│   │   └── env.py
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                  #   FastAPI app, CORS, startup/shutdown
│   │   ├── config.py                #   Settings via pydantic-settings (env vars)
│   │   ├── database.py              #   Async SQLAlchemy engine + session factory
│   │   │
│   │   ├── models/                  #   SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── school.py            #   schools (tenants)
│   │   │   ├── user.py              #   users (all roles)
│   │   │   ├── parent_student.py    #   parent_student (M2M)
│   │   │   ├── classe.py            #   classes
│   │   │   ├── student.py           #   students
│   │   │   ├── matiere.py           #   subjects (matieres)
│   │   │   ├── note.py              #   semester grades (notes)
│   │   │   ├── assignment.py        #   assignments
│   │   │   ├── assignment_grade.py  #   per-student assignment grades
│   │   │   ├── attendance.py        #   attendance records
│   │   │   ├── timetable.py         #   timetable slots
│   │   │   ├── fee_plan.py          #   fee plans
│   │   │   ├── invoice.py           #   invoices
│   │   │   ├── admission.py         #   admission applications
│   │   │   ├── notification.py      #   notifications
│   │   │   └── audit_log.py         #   audit trail
│   │   │
│   │   ├── schemas/                 #   Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── school.py
│   │   │   ├── user.py
│   │   │   ├── classe.py
│   │   │   ├── student.py
│   │   │   ├── matiere.py
│   │   │   ├── note.py
│   │   │   ├── assignment.py
│   │   │   ├── attendance.py
│   │   │   ├── timetable.py
│   │   │   ├── invoice.py
│   │   │   ├── admission.py
│   │   │   ├── notification.py
│   │   │   └── common.py            #   Pagination, error responses
│   │   │
│   │   ├── routers/                 #   API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              #   /auth/*
│   │   │   ├── schools.py           #   /schools/*
│   │   │   ├── classes.py           #   /classes/*
│   │   │   ├── students.py          #   /students/*, /classes/{id}/students
│   │   │   ├── subjects.py          #   /subjects/*
│   │   │   ├── grades.py            #   /grades/*
│   │   │   ├── assignments.py       #   /assignments/*
│   │   │   ├── attendance.py        #   /attendance/*
│   │   │   ├── timetable.py         #   /timetable/*
│   │   │   ├── portal_parent.py     #   /parent/*
│   │   │   ├── portal_student.py    #   /student/*
│   │   │   ├── invoices.py          #   /invoices/*
│   │   │   ├── admissions.py        #   /admissions/*
│   │   │   ├── notifications.py     #   /notifications/*
│   │   │   ├── dashboard.py         #   /dashboard/*
│   │   │   ├── export.py            #   /export/*
│   │   │   └── config.py           #   /config/*
│   │   │
│   │   ├── services/                #   Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── class_service.py
│   │   │   ├── student_service.py
│   │   │   ├── grade_service.py     #   Includes Moroccan curriculum seed data
│   │   │   ├── assignment_service.py
│   │   │   ├── attendance_service.py
│   │   │   ├── timetable_service.py
│   │   │   ├── invoice_service.py
│   │   │   ├── admission_service.py
│   │   │   ├── notification_service.py
│   │   │   ├── export_service.py
│   │   │   └── stats_service.py
│   │   │
│   │   ├── middleware/
│   │   │   ├── tenant.py            #   Injects school_id from JWT
│   │   │   └── rate_limiter.py      #   Auth endpoint rate limiting
│   │   │
│   │   ├── deps.py                  #   Dependency injection (get_db, get_current_user, require_role)
│   │   ├── security.py              #   JWT creation/verification, password hashing
│   │   ├── events.py                #   Event emitter for notifications
│   │   └── seed.py                  #   Seed script (super admin + Moroccan curriculum)
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_classes.py
│   │   ├── test_students.py
│   │   └── ...
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                        # React + TypeScript SPA
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                     #   Axios instance + interceptors
│   │   ├── auth/                    #   Auth context + hooks
│   │   ├── types/                   #   TypeScript interfaces
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── admin/               #   Admin-only views
│   │   │   ├── teacher/             #   Teacher views
│   │   │   ├── parent/              #   Parent portal
│   │   │   └── student/             #   Student portal
│   │   ├── components/              #   Reusable UI components
│   │   └── utils/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── docker-compose.yml               # PostgreSQL + Redis + pgAdmin
├── .env.example
├── README.md                        # This file
├── ARCHITECTURE.md
├── API.md
├── DATABASE.md
├── DEVELOPMENT.md
└── DEPLOYMENT.md
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+ & npm

### 1. Clone and start infrastructure

```bash
git clone https://github.com/SaadEddine-ware/MainPixel.git
cd MainPixel
cp .env.example .env
docker compose up -d
```

This starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- pgAdmin on `localhost:5050` (admin@admin.com / admin)

### 2. Set up backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs` (Swagger UI)

### 3. Set up frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: `http://localhost:5173`

### 4. Default credentials

| Role | Email | Password |
|------|-------|----------|
| Super Admin | superadmin@mainpixel.ma | ChangeMe123! |

Change this immediately in production.

---

## Features

### Core Academic
- **Class Management**: Create classes by level/year/branch, rename, delete
- **Student Management**: Add, edit, import via CSV, max 60 per class
- **Subject Management**: Pre-seeded Moroccan curriculum (all levels + branches), custom subjects
- **Grade Management**: Semester grades per subject, weighted averages, final calculations
- **Assignment Management**: Create assignments with coefficients, per-student grading, sync to final notes

### Attendance
- **Bulk recording**: Mark entire class in one request
- **Status tracking**: Present, absent, late, excused
- **Period support**: Per-period or full-day
- **Justification workflow**: Parents upload justification documents
- **Absence alerts**: Automatic notification when threshold exceeded

### Timetable
- **Schedule builder**: Admin creates weekly timetable per class
- **Conflict detection**: Teacher and room double-booking prevention
- **Teacher view**: Personal schedule across all assigned classes

### Parent Portal
- **Children list**: View all linked children
- **Read-only access**: Grades, attendance, timetable per child
- **Absence justification**: Upload justification documents
- **Invoice viewing**: Check payment status

### Student Portal
- **Self-only access**: Own grades, attendance, timetable
- **Same API as parent portal** but without the child-id indirection

### Finance
- **Fee plans**: Monthly, quarterly, annual, one-time
- **Invoice generation**: Bulk generate for class/level
- **Payment tracking**: Mark paid, overdue status
- **Audit trail**: All amount changes logged

### Admissions
- **Public application form**: No pre-existing account needed
- **Status workflow**: submitted → under_review → accepted/rejected/waitlisted
- **Auto-provisioning**: Acceptance creates student + parent account in one transaction

### Notifications
- **Event-driven**: Grades published, absence alerts, invoice due, announcements
- **Multi-channel**: In-app (MVP), email (SMTP), SMS (later), push (mobile later)
- **Redis queue**: Async processing, no blocking on core operations

### Analytics Dashboard
- **Overview**: Student/teacher/class counts, attendance rate
- **Grade distribution**: Per class/subject
- **Attendance trends**: Over time periods
- **Financial summary**: Paid vs overdue

### Export & Reports
- **HTML reports**: Class lists, grade sheets
- **PDF export**: Certificates, transcripts
- **CSV import**: Student lists
- **Full backup**: ZIP export of school data

---

## Roles & Permissions

| Action | super_admin | school_admin | teacher | parent | student |
|--------|:-----------:|:------------:|:-------:|:------:|:-------:|
| Manage other schools | ✅ | ❌ | ❌ | ❌ | ❌ |
| Create/delete users in own school | ❌ | ✅ | ❌ | ❌ | ❌ |
| Enter grades | ❌ | ✅ | ✅ | ❌ | ❌ |
| View grades | ❌ | ✅ all | ✅ own classes | ✅ own children | ✅ self |
| Record attendance | ❌ | ✅ | ✅ own classes | ❌ | ❌ |
| View attendance | ❌ | ✅ all | ✅ own classes | ✅ own children | ✅ self |
| Manage timetables | ❌ | ✅ | ❌ | ❌ | ❌ |
| Access invoices | ❌ | ✅ | ❌ | ✅ own only | ❌ |
| Manage admissions | ❌ | ✅ | ❌ | ❌ | ❌ |
| View notifications | ✅ | ✅ | ✅ | ✅ | ✅ |
| View dashboard | ✅ all schools | ✅ own school | ✅ own stats | ❌ | ❌ |

---

## API Overview

Base URL: `http://localhost:8000/api`

| Module | Endpoints | Description |
|--------|-----------|-------------|
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` | JWT authentication |
| Schools | `POST /schools/register`, `GET /schools/{id}` | Tenant management |
| Classes | `GET/POST /classes`, `GET/PUT/DELETE /classes/{id}` | Class CRUD |
| Students | `GET/POST /classes/{id}/students`, `GET/PUT/DELETE /students/{id}` | Student CRUD + CSV import |
| Subjects | `GET/POST /subjects`, `GET/PUT/DELETE /subjects/{id}` | Subject CRUD + seed |
| Grades | `GET/PUT /grades/{student_id}`, `GET /grades/{student_id}/averages` | Semester grades |
| Assignments | `GET/POST /assignments`, `GET/PUT/DELETE /assignments/{id}` | Assignment CRUD + grading |
| Attendance | `POST /attendance`, `GET /attendance`, `PATCH /attendance/{id}` | Attendance records |
| Timetable | `POST/PUT /timetable/slots`, `GET /timetable` | Schedule management |
| Parent Portal | `GET /parent/children`, `GET /parent/children/{id}/*` | Read-only child data |
| Student Portal | `GET /student/grades`, `GET /student/attendance`, `GET /student/timetable` | Read-only self data |
| Invoices | `POST /invoices/generate`, `GET /invoices`, `PATCH /invoices/{id}/mark-paid` | Fee management |
| Admissions | `POST /admissions/apply`, `GET /admissions`, `PATCH /admissions/{id}/status` | Application workflow |
| Notifications | `GET /notifications`, `PATCH /notifications/{id}/read` | Notification center |
| Dashboard | `GET /dashboard/overview`, `GET /dashboard/grades-distribution` | Analytics |
| Export | `GET /export/{class_id}/html`, `GET /export/{class_id}/pdf`, `GET /export/{student_id}/certificate` | Reports |
| Config | `GET/PUT /config` | School configuration |

Full API documentation: [API.md](./API.md)

---

## Database

Full schema documentation: [DATABASE.md](./DATABASE.md)

### Quick Reference

| Table | Purpose |
|-------|---------|
| `schools` | Tenant definitions (multi-tenancy root) |
| `users` | All user accounts (admin, teacher, parent, student) |
| `parent_student` | Parent ↔ student many-to-many |
| `classes` | Class definitions (level, year, branch) |
| `students` | Student records (linked to class) |
| `matieres` | Subjects with coefficients |
| `notes` | Semester grades per student per subject |
| `assignments` | Individual assignments (tests, homework) |
| `assignment_grades` | Per-student grade per assignment |
| `attendance_records` | Daily/period attendance |
| `timetable_slots` | Weekly schedule per class |
| `fee_plans` | Fee structure definitions |
| `invoices` | Generated invoices per student |
| `admission_applications` | New student applications |
| `notifications` | User notifications |
| `audit_logs` | Activity audit trail |

---

## Deployment

Full deployment guide: [DEPLOYMENT.md](./DEPLOYMENT.md)

### Production Checklist

- [ ] Change all default passwords
- [ ] Set `SECRET_KEY` to a random 64-char string
- [ ] Set `DATABASE_URL` to production PostgreSQL
- [ ] Set `REDIS_URL` to production Redis
- [ ] Configure CORS origins for your domain
- [ ] Set up SSL/TLS (reverse proxy with nginx/caddy)
- [ ] Configure automated backups (pg_dump cron)
- [ ] Register with CNDP (Moroccan data protection)
- [ ] Set up email SMTP credentials
- [ ] Deploy frontend to CDN/Vercel/Netlify

---

## Legal Requirements

Before commercial launch in Morocco:

1. **CNDP Registration**: Register personal data processing with the National Commission for Data Protection (minors' data is sensitive)
2. **Privacy Policy**: Clear terms presented at school registration
3. **Data Processing Agreement (DPA)**: Between platform and each client school
4. **Data Portability**: Schools can export their data at any time

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Rules

- Run `pytest` before pushing
- Run `ruff check` and `ruff format` for Python linting
- Run `npm run lint` for frontend
- Never commit secrets or API keys
- All database changes must go through Alembic migrations

---

## License

Proprietary — All rights reserved.

---

## Contact

- GitHub: [SaadEddine-ware](https://github.com/SaadEddine-ware)
