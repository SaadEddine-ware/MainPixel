# Phase Log — MainPixel

This file tracks all development phases and their completion status.

**Last Updated:** 2026-08-30

---

## Phase 0: Documentation & Project Reorg — ✅ COMPLETED

**Date:** 2026-08-29
**Status:** completed

### Files Created
- `README.md` — Project overview, quick start, features, roles
- `ARCHITECTURE.md` — System design, multi-tenancy, auth, data flow, security
- `API.md` — Full REST API reference (50+ endpoints)
- `DATABASE.md` — Complete schema (16 tables, indexes, RLS)
- `DEVELOPMENT.md` — Local dev setup, code style, testing
- `DEPLOYMENT.md` — Docker/VPS deploy, SSL, backups, security
- `RULES.md` — Working constraints and self-check rules
- `PHASE_LOG.md` — This file
- `.env.example` — Environment variable template
- `.gitignore` — Git ignore rules
- `docker-compose.yml` — Local dev infrastructure
- `docker-compose.prod.yml` — Production infrastructure

### Files Modified
- None (initial documentation phase)

### Tests
- N/A (documentation only)

### Deviations from Docs
- None

### Notes
- Full documentation suite created before any code
- Multi-tenancy architecture defined (school_id on every table)
- 10 phases defined in implementation order
- Legacy Python desktop apps preserved in `legacy/` (currently in `admin/` and `teacher/`)

### Next
- Phase 0 (continued): Project setup (FastAPI, Docker, PostgreSQL, Alembic)

---

## Phase 0: Project Setup — ✅ COMPLETED

**Date:** 2026-08-30
**Status:** completed

### Completed Work
- [x] Created `backend/` project structure
- [x] FastAPI app with CORS + tenant middleware
- [x] SQLAlchemy async engine + PostgreSQL connection
- [x] Pydantic settings with `.env` support
- [x] `School` model (UUID PK, slug, contact info)
- [x] `User` model (UUID PK, FK to school, 5 roles enum)
- [x] Alembic configuration + async env
- [x] JWT security (access + refresh tokens, bcrypt hashing)
- [x] Tenant middleware (extracts user_id, role, school_id from JWT)
- [x] Auth router (`/auth/login`, `/auth/refresh`)
- [x] Seed script (1 school, 5 users across all roles)
- [x] Docker Compose (PostgreSQL 16, Redis 7, pgAdmin)
- [x] Server setup: Hetzner VPS configured (Python 3.14, Docker, Node.js, tmux)
- [x] Verified: health check, login, JWT generation all working

### Verified Endpoints
- `GET /health` → `{"status": "healthy"}`
- `POST /api/v1/auth/login` → JWT access + refresh tokens

### Server Access
- IP: 178.105.115.123
- SSH: `ssh -i ~/.ssh/orema_deploy root@178.105.115.123`
- API: `http://178.105.115.123:8000` (running in tmux session `api`)
- pgAdmin: `http://178.105.115.123:5050` (admin@admin.com / admin)

### Next
- Phase 1: Core Academic (Classes, Students, Subjects, Grades, Assignments)

---

## Phase 1: Core Academic — ✅ COMPLETED

**Date:** 2026-08-30
**Status:** completed

### Completed Work
- [x] Classes CRUD (model, schema, router)
- [x] Students CRUD + CSV import
- [x] Subjects CRUD + Moroccan curriculum seed (4 levels)
- [x] Notes (semester grades) CRUD + bulk create
- [x] Assignments CRUD + grades
- [x] Moyenne calculation (weighted average by coefficient)
- [x] HTML bulletin export
- [x] Audit logging utility
- [x] All endpoints tested on server

### API Endpoints
- `GET/POST /api/v1/classes/` — Class CRUD
- `GET/POST /api/v1/students/` — Student CRUD
- `POST /api/v1/students/import-csv` — CSV import
- `GET/POST /api/v1/subjects/` — Subject CRUD
- `GET/POST /api/v1/notes/` — Notes CRUD
- `POST /api/v1/notes/bulk` — Bulk note creation
- `GET /api/v1/notes/student/{id}/moyenne` — Calculate moyenne
- `GET/POST /api/v1/assignments/` — Assignment CRUD
- `GET/POST /api/v1/assignments/{id}/grades` — Grade management
- `POST /api/v1/curriculum/seed-curriculum` — Seed Moroccan curriculum
- `GET /api/v1/curriculum/curriculum` — Get curriculum data
- `GET /api/v1/export/bulletin/{id}` — HTML bulletin export

### Next
- Phase 2: Attendance Module

---

## Phase 2: Attendance — ⏳ PENDING

**Date:** Not started
**Status:** pending

### Next
- Phase 3: Timetable Module

---

## Phase 3: Timetable — ⏳ PENDING

**Date:** Not started
**Status:** pending

### Next
- Phase 4: Parent + Student Portals

---

## Phase 4: Portals — ⏳ PENDING

**Date:** Not started
**Status:** pending

### Next
- Phase 5: Fees & Invoicing

---

## Phase 5: Finance — ⏳ PENDING

**Date:** Not started
**Status:** pending

### Next
- Phase 6: Admissions

---

## Phase 6: Admissions — ⏳ PENDING

**Date:** Not started
**Status:** pending

### Next
- Phase 7: Notifications

---

## Phase 7: Notifications — ⏳ PENDING

**Date:** Not started
**Status:** pending

### Next
- Phase 8: Analytics Dashboard

---

## Phase 8: Dashboard — ⏳ PENDING

**Date:** Not started
**Status:** pending

### Next
- Phase 9: Frontend (React + TypeScript)

---

## Phase 9: Frontend — ⏳ PENDING

**Date:** Not started
**Status:** pending

---

## Summary

| Phase | Name | Status | Date |
|-------|------|--------|------|
| 0 | Documentation & Project Reorg | ✅ COMPLETED | 2026-08-29 |
| 0 | Project Setup | ✅ COMPLETED | 2026-08-30 |
| 1 | Core Academic | ✅ COMPLETED | 2026-08-30 |
| 2 | Attendance | ⏳ PENDING | — |
| 3 | Timetable | ⏳ PENDING | — |
| 4 | Portals | ⏳ PENDING | — |
| 5 | Finance | ⏳ PENDING | — |
| 6 | Admissions | ⏳ PENDING | — |
| 7 | Notifications | ⏳ PENDING | — |
| 8 | Dashboard | ⏳ PENDING | — |
| 9 | Frontend | ⏳ PENDING | — |
