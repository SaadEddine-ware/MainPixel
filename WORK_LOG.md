# Work Log — MainPixel

## 2026-08-30

### 08:00 - 08:30 (0.5h) — Phase 0: Server Setup
- SSH into Hetzner server
- Installed Docker, Python 3.14, Node.js, tmux
- Cloned repo to /opt/MainPixel
- Started PostgreSQL 16, Redis 7, pgAdmin
- Created backend structure: FastAPI, SQLAlchemy async, JWT auth
- Seeded database: 1 school, 5 users
- Verified: health check, login, JWT tokens working
- Fixed bcrypt 5.x → 4.2.1 for passlib compatibility

### 08:30 - 09:00 (0.5h) — Phase 1: Core Academic
- Created models: SchoolClass, Student, Subject, Note, Assignment, Grade, AuditLog
- Created schemas: all Create/Update/Out for each model
- Created CRUD routers: classes, students, subjects, notes, assignments
- Moroccan curriculum seed: primary, middle, lycee_sciences, lycee_lettres
- Moyenne calculation endpoint (weighted average by coefficient)
- HTML bulletin export endpoint
- Audit logging utility
- CSV import endpoint for students
- Bulk notes endpoint
- All endpoints tested and verified on server

### Verified Endpoints
| Endpoint | Method | Status |
|----------|--------|--------|
| /health | GET | ✅ |
| /api/v1/auth/login | POST | ✅ |
| /api/v1/auth/refresh | POST | ✅ |
| /api/v1/classes/ | GET/POST | ✅ |
| /api/v1/students/ | GET/POST | ✅ |
| /api/v1/students/import-csv | POST | ✅ |
| /api/v1/subjects/ | GET/POST | ✅ |
| /api/v1/notes/ | GET/POST | ✅ |
| /api/v1/notes/bulk | POST | ✅ |
| /api/v1/notes/student/{id}/moyenne | GET | ✅ |
| /api/v1/assignments/ | GET/POST | ✅ |
| /api/v1/assignments/{id}/grades | GET/POST | ✅ |
| /api/v1/curriculum/seed-curriculum | POST | ✅ |
| /api/v1/curriculum/curriculum | GET | ✅ |
| /api/v1/export/bulletin/{id} | GET | ✅ |

### Server Access
- IP: 178.105.115.123
- SSH: `ssh -i ~/.ssh/orema_deploy root@178.105.115.123`
- API: `http://178.105.115.123:8000` (tmux session `api`)
- pgAdmin: `http://178.105.115.123:5050`

### Git Commits
- b10ea7d docs: add complete documentation suite
- 7688c8a feat(backend): Phase 0 - FastAPI core
- 937522b fix(backend): add missing models/base.py
- 18b9506 fix(backend): pin bcrypt 4.2.1
- 9579575 docs: mark Phase 0 project setup complete
- 1cd6a72 feat(backend): Phase 1 - classes, students, subjects, notes, assignments, curriculum
- c3e3b0a feat: Phase 1 core academic models + CRUD on server
- 7b49c2a feat(backend): Phase 1 complete - export + audit logging
