# Working Rules — MainPixel

This file defines the constraints and workflow rules I must follow while working on MainPixel.

---

## Rule 1: Documentation Is The Source Of Truth

Before starting ANY task, I MUST:

1. **Read the relevant documentation**:
   - `ARCHITECTURE.md` — for system design decisions
   - `API.md` — for endpoint contracts
   - `DATABASE.md` — for schema and table definitions
   - `DEVELOPMENT.md` — for code structure and conventions
   - `DEPLOYMENT.md` — for infrastructure

2. **Verify the task is documented**: If the task is not described in any doc, I MUST ask the user before proceeding. Never build features that aren't in the docs.

3. **Follow the documented patterns**: Code structure, naming conventions, API contracts, and database schema MUST match what's written in the docs.

---

## Rule 2: Phase Log Must Be Updated

After completing each phase or significant milestone, I MUST:

1. Open `PHASE_LOG.md`
2. Add a new entry with:
   - Phase number and name
   - Date/time
   - Files created/modified
   - Tests passing (yes/no)
   - Any deviations from documentation (with reason)
   - Next phase to be worked on

---

## Rule 3: Daily Commits

At the end of each working session (or when significant progress is made), I MUST:

1. Run `git status` and `git diff` to review changes
2. Stage all relevant files (never secrets or .env)
3. Write a clear commit message following Conventional Commits:
   ```
   feat: add class management API endpoints
   fix: correct grade average calculation
   docs: update API documentation for attendance
   test: add tenancy isolation tests
   ```
4. Commit with a descriptive message

---

## Rule 4: Before Every Code Change Checklist

- [ ] Is this change described in the documentation?
- [ ] Does the API contract match `API.md`?
- [ ] Does the schema match `DATABASE.md`?
- [ ] Does the code structure match `DEVELOPMENT.md`?
- [ ] Am I following the correct phase order from `README.md`?
- [ ] Will this break existing functionality?
- [ ] Do I need to create/update a migration?

---

## Rule 5: Phase Order (from README.md)

I MUST follow this implementation order:

```
Phase 0: Project Reorg + Foundation (Auth + Multi-tenancy)
Phase 1: Core Academic (Classes, Students, Subjects, Grades, Assignments)
Phase 2: Attendance Module
Phase 3: Timetable Module
Phase 4: Parent + Student Portals
Phase 5: Fees & Invoicing
Phase 6: Admissions
Phase 7: Notifications
Phase 8: Analytics Dashboard
Phase 9: Frontend (React + TypeScript)
```

I MUST NOT skip ahead to a later phase without completing the current one first. Dependencies between phases are real and must be respected.

---

## Rule 6: Git Commit Protocol

### Before Committing

```bash
# 1. Check what changed
git status
git diff --stat

# 2. Review the diff for secrets/keys
git diff | grep -i "password\|secret\|token\|key"

# 3. Stage files
git add <files>

# 4. Verify no secrets staged
git diff --cached | grep -i "password\|secret\|token\|key"

# 5. Commit
git commit -m "type: description"
```

### Commit Message Format

```
<type>: <description>

[optional body]
```

**Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation only
- `test` — Adding tests
- `refactor` — Code restructuring (no feature change)
- `chore` — Build, config, dependency updates
- `phase` — Phase completion marker

---

## Rule 7: What To Log In PHASE_LOG.md

Each entry must include:

```markdown
## Phase X: [Name] — [Status]

**Date:** YYYY-MM-DD HH:MM
**Status:** in_progress | completed | blocked

### Files Created
- `backend/app/models/school.py`
- `backend/app/routers/auth.py`
- ...

### Files Modified
- `backend/app/main.py` — added router includes
- ...

### Tests
- [x] test_create_school
- [x] test_login
- [ ] test_cross_school_isolation (pending)

### Deviations from Docs
- None / [describe deviation and reason]

### Notes
- Any important observations or decisions made

### Next
- [What comes next]
```

---

## Rule 8: Security Checks

Before any commit that involves:
- Authentication code
- Database queries
- User input handling

I MUST verify:
- [ ] No hardcoded secrets
- [ ] No SQL injection vectors (using ORM parameterized queries)
- [ ] school_id is enforced in all queries
- [ ] Role checks are present on protected endpoints
- [ ] Input validation is done via Pydantic schemas

---

## Rule 9: Documentation Updates

If during implementation I discover:
- A new table is needed (not in DATABASE.md)
- A new endpoint is needed (not in API.md)
- A different architecture approach (not in ARCHITECTURE.md)

I MUST:
1. **First**: Update the relevant documentation
2. **Then**: Implement the code change
3. **Finally**: Log the deviation in PHASE_LOG.md

Never write code that contradicts the documentation without updating the docs first.

---

## Rule 10: Working Directory

All work happens in `/home/saad/Desktop/MainPixel/`

- Legacy code stays in `legacy/` (admin/, teacher/) — DO NOT MODIFY
- New backend goes in `backend/`
- New frontend goes in `frontend/`
- Documentation stays in root

---

## Self-Check Script

Before starting each session, I will mentally verify:

1. Am I working on the correct phase?
2. Have I read the relevant docs?
3. Is my last commit pushed/logged?
4. Is PHASE_LOG.md up to date?
