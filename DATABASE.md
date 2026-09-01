# Database Schema — MainPixel

PostgreSQL 16 database with multi-tenant architecture.

---

## Table of Contents

- [Conventions](#conventions)
- [Entity Relationship Diagram](#entity-relationship-diagram)
- [Table Definitions](#table-definitions)
  - [schools](#schools)
  - [users](#users)
  - [parent_student](#parent_student)
  - [classes](#classes)
  - [students](#students)
  - [matieres](#matieres)
  - [notes](#notes)
  - [assignments](#assignments)
  - [assignment_grades](#assignment_grades)
  - [attendance_records](#attendance_records)
  - [timetable_slots](#timetable_slots)
  - [fee_plans](#fee_plans)
  - [invoices](#invoices)
  - [admission_applications](#admission_applications)
  - [notifications](#notifications)
  - [audit_logs](#audit_logs)
- [Indexes](#indexes)
- [Row-Level Security](#row-level-security)
- [Migrations](#migrations)
- [Seed Data](#seed-data)

---

## Conventions

| Convention | Rule |
|-----------|------|
| Primary Keys | UUID v4 (generated in Python via `uuid4()`) |
| Timestamps | ISO 8601 UTC (`created_at`, `updated_at`) |
| Multi-tenancy | Every table (except `schools`) has `school_id` FK |
| Soft deletes | Use `is_active` boolean, never hard-delete users |
| Naming | `snake_case` for columns and tables |
| Foreign Keys | `{table}_id` pattern (e.g., `school_id`, `student_id`) |
| Enums | PostgreSQL native `ENUM` types where possible, otherwise `VARCHAR` with check constraints |

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              schools                                        │
│  id (UUID PK)                                                               │
│  name, slug, plan, levels_config (JSON), status                             │
└───────────┬─────────────────────────────────────────────────────────────────┘
            │
            ├─── users (school_id FK)
            │    id (UUID PK), email, password_hash, role, full_name, ...
            │    │
            │    ├─── parent_student (parent_user_id FK)
            │    │         │
            │    │         └─── student_user_id (nullable FK → users)
            │    │
            │    └─── timetable_slots.teacher_id FK
            │
            ├─── classes (school_id FK)
            │    id (UUID PK), level_key, year_name, name, branch, ...
            │    │
            │    ├─── students (class_id FK, school_id FK)
            │    │    id (UUID PK), code_massar, full_name, ...
            │    │    │
            │    │    ├─── notes (student_id FK, school_id FK)
            │    │    │    id (UUID PK), matiere_id FK, semester, valeur
            │    │    │
            │    │    ├─── assignment_grades (student_id FK, school_id FK)
            │    │    │    id (UUID PK), assignment_id FK, valeur
            │    │    │
            │    │    ├─── attendance_records (student_id FK, school_id FK)
            │    │    │    id (UUID PK), classe_id FK, date, status, period
            │    │    │
            │    │    ├─── invoices (student_id FK, school_id FK)
            │    │    │    id (UUID PK), fee_plan_id FK, amount_due, status
            │    │    │
            │    │    └─── timetable_slots (classe_id FK)
            │    │
            │    └─── assignments (classe_id FK, school_id FK)
            │         id (UUID PK), matiere_id FK, semester, title, ...
            │
            ├─── matieres (school_id FK)
            │    id (UUID PK), name, coefficient, level_key, year_name, branch
            │
            ├─── fee_plans (school_id FK)
            │    id (UUID PK), name, amount, frequency, level_key
            │
            ├─── admission_applications (school_id FK)
            │    id (UUID PK), applicant_name, status, ...
            │
            ├─── notifications (school_id FK)
            │    id (UUID PK), recipient_user_id FK, type, title, body
            │
            └─── audit_logs (school_id FK)
                 id (UUID PK), user_name, action, entity_type, entity_id
```

---

## Table Definitions

### schools

Tenants. The root of multi-tenancy. Each school is an isolated tenant.

```sql
CREATE TABLE schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL UNIQUE,
    plan VARCHAR(20) NOT NULL DEFAULT 'trial'
        CHECK (plan IN ('trial', 'free', 'standard', 'premium')),
    levels_config JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'trial'
        CHECK (status IN ('active', 'suspended', 'trial')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_schools_slug ON schools(slug);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `name` | VARCHAR(200) | No | School display name |
| `slug` | VARCHAR(200) | No | URL-safe identifier (unique) |
| `plan` | VARCHAR(20) | No | Subscription plan |
| `levels_config` | JSONB | No | Education structure (see below) |
| `status` | VARCHAR(20) | No | Account status |
| `created_at` | TIMESTAMP | No | Creation timestamp |
| `updated_at` | TIMESTAMP | No | Last update timestamp |

**`levels_config` JSON structure:**

```json
{
  "levels": {
    "primary": "Primaire",
    "middle": "Collège",
    "lycee": "Lycée"
  },
  "years_structure": {
    "primary": ["1", "2", "3", "4", "5", "6"],
    "middle": ["1", "2", "3"],
    "lycee": ["1", "2", "3"]
  }
}
```

---

### users

All user accounts: admins, teachers, parents, and students (if they need login).

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL
        CHECK (role IN ('super_admin', 'school_admin', 'teacher', 'parent', 'student')),
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (school_id, email)
);

CREATE INDEX idx_users_school_id ON users(school_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(school_id, role);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `school_id` | UUID | No | Tenant FK |
| `email` | VARCHAR(255) | No | Login email (unique per school) |
| `password_hash` | VARCHAR(255) | No | bcrypt hashed password |
| `role` | VARCHAR(20) | No | User role |
| `full_name` | VARCHAR(200) | No | Display name |
| `phone` | VARCHAR(20) | Yes | Phone number (for SMS) |
| `is_active` | BOOLEAN | No | Soft delete flag |
| `last_login_at` | TIMESTAMP | Yes | Last successful login |
| `created_at` | TIMESTAMP | No | Creation timestamp |
| `updated_at` | TIMESTAMP | No | Last update timestamp |

**Role descriptions:**

| Role | Description |
|------|-------------|
| `super_admin` | Platform-wide admin (manages schools). `school_id` is nullable for this role. |
| `school_admin` | School administrator (full access within school) |
| `teacher` | Teacher (enters grades, records attendance) |
| `parent` | Parent (read-only view of children's data) |
| `student` | Student (read-only view of own data) |

---

### parent_student

Many-to-many relationship between parents and their children.

```sql
CREATE TABLE parent_student (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    parent_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (school_id, parent_user_id, student_id)
);

CREATE INDEX idx_parent_student_parent ON parent_student(parent_user_id);
CREATE INDEX idx_parent_student_student ON parent_student(student_id);
```

---

### classes

School classes (e.g., "3ème A", "6ème B").

```sql
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    level_key VARCHAR(50) NOT NULL,
    level_name VARCHAR(100) NOT NULL,
    year_name VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    branch VARCHAR(100) DEFAULT '',
    academic_year VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (school_id, level_key, year_name, name, branch)
);

CREATE INDEX idx_classes_school_id ON classes(school_id);
CREATE INDEX idx_classes_level ON classes(school_id, level_key, year_name);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `school_id` | UUID | No | Tenant FK |
| `level_key` | VARCHAR(50) | No | Level identifier (primary, middle, lycee) |
| `level_name` | VARCHAR(100) | No | Display name (Primaire, Collège, Lycée) |
| `year_name` | VARCHAR(50) | No | Year within level (1, 2, 3, ...) |
| `name` | VARCHAR(100) | No | Class name (A, B, ...) |
| `branch` | VARCHAR(100) | No | Branch (empty for primary/middle) |
| `academic_year` | VARCHAR(50) | Yes | e.g., "2025-2026" |

---

### students

Student records linked to a class.

```sql
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    student_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    code_massar VARCHAR(50),
    full_name VARCHAR(200) NOT NULL,
    birth_date VARCHAR(20),
    sexe VARCHAR(10),
    address VARCHAR(300),
    father_name VARCHAR(200),
    mother_name VARCHAR(200),
    comment VARCHAR(500) DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (school_id, code_massar),
    CHECK (code_massar IS NULL OR code_massar != '')
);

CREATE INDEX idx_students_school_id ON students(school_id);
CREATE INDEX idx_students_class_id ON students(class_id);
CREATE INDEX idx_students_code_massar ON students(school_id, code_massar);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `school_id` | UUID | No | Tenant FK |
| `class_id` | UUID | No | Class FK |
| `student_user_id` | UUID | Yes | Link to login account (if student has one) |
| `code_massar` | VARCHAR(50) | Yes | National student ID (unique per school) |
| `full_name` | VARCHAR(200) | No | Student name |
| `birth_date` | VARCHAR(20) | Yes | Date of birth |
| `sexe` | VARCHAR(10) | Yes | Gender |
| `address` | VARCHAR(300) | Yes | Home address |
| `father_name` | VARCHAR(200) | Yes | Father's name |
| `mother_name` | VARCHAR(200) | Yes | Mother's name |
| `comment` | VARCHAR(500) | No | Notes |
| `sort_order` | INTEGER | No | Display order within class |

**Constraint: Max 60 students per class** (enforced in application layer, not DB).

---

### matieres

Subjects with coefficients, scoped to level/year/branch.

```sql
CREATE TABLE matieres (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    coefficient FLOAT NOT NULL DEFAULT 1.0,
    level_key VARCHAR(50) NOT NULL,
    year_name VARCHAR(50),
    branch VARCHAR(100) DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_matieres_school_id ON matieres(school_id);
CREATE INDEX idx_matieres_level ON matieres(school_id, level_key, year_name);
```

**Moroccan Curriculum Examples:**

| Level | Year | Subject | Coefficient |
|-------|------|---------|-------------|
| primary | 1 | Langue arabe | 3 |
| primary | 1 | Mathematiques | 3 |
| middle | 3 | Informatique | 1 |
| lycee | 2 | Mathematiques (1BAC SM) | 9 |
| lycee | 3 | Physique-Chimie (2BAC SP) | 9 |

---

### notes

Semester grades per student per subject.

```sql
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    matiere_id UUID NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    semester INTEGER NOT NULL CHECK (semester IN (1, 2)),
    valeur FLOAT NOT NULL CHECK (valeur >= 0 AND valeur <= 20),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (school_id, student_id, matiere_id, semester)
);

CREATE INDEX idx_notes_student ON notes(student_id);
CREATE INDEX idx_notes_matiere ON notes(matiere_id);
CREATE INDEX idx_notes_semester ON notes(school_id, student_id, semester);
```

**Grade scale:** 0-20 (Moroccan system). Passing is 10/20.

---

### assignments

Individual assignments (tests, homework, projects).

```sql
CREATE TABLE assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    classe_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    matiere_id UUID NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    semester INTEGER NOT NULL CHECK (semester IN (1, 2)),
    title VARCHAR(200) NOT NULL,
    coefficient FLOAT DEFAULT 1.0,
    date VARCHAR(20) DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_assignments_class ON assignments(classe_id);
CREATE INDEX idx_assignments_matiere ON assignments(matiere_id);
CREATE INDEX idx_assignments_semester ON assignments(school_id, classe_id, matiere_id, semester);
```

---

### assignment_grades

Per-student grade for each assignment.

```sql
CREATE TABLE assignment_grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    valeur FLOAT NOT NULL CHECK (valeur >= 0 AND valeur <= 20),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (school_id, assignment_id, student_id)
);

CREATE INDEX idx_assignment_grades_assignment ON assignment_grades(assignment_id);
CREATE INDEX idx_assignment_grades_student ON assignment_grades(student_id);
```

**Business rule:** Subject average = weighted average of all assignment grades for that subject. Can be synced to `notes` table via `/assignments/sync`.

---

### attendance_records

Daily/period attendance tracking.

```sql
CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    classe_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status VARCHAR(10) NOT NULL
        CHECK (status IN ('present', 'absent', 'late', 'excused')),
    period VARCHAR(20) DEFAULT 'full_day',
    recorded_by UUID NOT NULL REFERENCES users(id),
    justification_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (school_id, student_id, date, period)
);

CREATE INDEX idx_attendance_student ON attendance_records(student_id);
CREATE INDEX idx_attendance_class_date ON attendance_records(classe_id, date);
CREATE INDEX idx_attendance_date ON attendance_records(school_id, date);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `school_id` | UUID | No | Tenant FK |
| `student_id` | UUID | No | Student FK |
| `classe_id` | UUID | No | Class FK |
| `date` | DATE | No | Attendance date |
| `status` | VARCHAR(10) | No | present/absent/late/excused |
| `period` | VARCHAR(20) | No | Period identifier or "full_day" |
| `recorded_by` | UUID | No | Teacher who recorded this |
| `justification_note` | TEXT | Yes | Justification text |

---

### timetable_slots

Weekly class schedule.

```sql
CREATE TABLE timetable_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    classe_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    matiere_id UUID NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    room VARCHAR(100),
    academic_year VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CHECK (start_time < end_time)
);

CREATE INDEX idx_timetable_class ON timetable_slots(classe_id, academic_year);
CREATE INDEX idx_timetable_teacher ON timetable_slots(teacher_id, academic_year);
CREATE INDEX idx_timetable_day ON timetable_slots(day_of_week);
```

**Day of week:** 0 = Monday, 6 = Sunday (ISO standard).

**Conflict detection** (application-level):
1. Same teacher cannot have overlapping slots on the same day
2. Same room cannot have overlapping slots at the same time

---

### fee_plans

Fee structure definitions.

```sql
CREATE TABLE fee_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    frequency VARCHAR(20) NOT NULL
        CHECK (frequency IN ('monthly', 'quarterly', 'annual', 'one_time')),
    level_key VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fee_plans_school ON fee_plans(school_id);
```

---

### invoices

Generated invoices per student.

```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    fee_plan_id UUID NOT NULL REFERENCES fee_plans(id) ON DELETE CASCADE,
    amount_due DECIMAL(10,2) NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'overdue', 'cancelled')),
    paid_at TIMESTAMP,
    payment_method VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invoices_school ON invoices(school_id);
CREATE INDEX idx_invoices_student ON invoices(student_id);
CREATE INDEX idx_invoices_status ON invoices(school_id, status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
```

---

### admission_applications

New student applications.

```sql
CREATE TABLE admission_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    applicant_name VARCHAR(200) NOT NULL,
    birth_date DATE,
    desired_level VARCHAR(50),
    desired_year VARCHAR(50),
    parent_name VARCHAR(200),
    parent_phone VARCHAR(20),
    parent_email VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'submitted'
        CHECK (status IN ('submitted', 'under_review', 'accepted', 'rejected', 'waitlisted')),
    documents JSONB DEFAULT '[]',
    submitted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewed_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_admissions_school ON admission_applications(school_id);
CREATE INDEX idx_admissions_status ON admission_applications(school_id, status);
```

**`documents` JSON structure:**

```json
[
  {
    "type": "birth_certificate",
    "url": "/uploads/admission/{uuid}_birth.pdf",
    "uploaded_at": "2026-08-29T10:00:00Z"
  }
]
```

---

### notifications

User notifications.

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    recipient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(30) NOT NULL
        CHECK (type IN ('grade_published', 'absence_alert', 'absence_threshold',
                        'invoice_due', 'invoice_overdue', 'announcement',
                        'admission_status')),
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'in_app'
        CHECK (channel IN ('in_app', 'email', 'sms', 'push')),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_recipient ON notifications(recipient_user_id, is_read);
CREATE INDEX idx_notifications_school ON notifications(school_id);
```

---

### audit_logs

Activity audit trail for compliance and debugging.

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    user_name VARCHAR(100) DEFAULT 'system',
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_school ON audit_logs(school_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(school_id, entity_type, entity_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(school_id, created_at);
```

**Action values:** `create`, `update`, `delete`, `import`, `rename`, `login`, `logout`, `grade_change`, `payment`

---

## Indexes

### Performance Indexes (already defined in tables above)

| Table | Index | Purpose |
|-------|-------|---------|
| `users` | `idx_users_school_id` | Filter users by school |
| `users` | `idx_users_email` | Login lookup |
| `users` | `idx_users_role` | Filter by role within school |
| `classes` | `idx_classes_school_id` | List classes by school |
| `classes` | `idx_classes_level` | Filter by level + year |
| `students` | `idx_students_class_id` | List students in class |
| `students` | `idx_students_code_massar` | Lookup by Massar code |
| `notes` | `idx_notes_student` | Get student's grades |
| `notes` | `idx_notes_semester` | Filter by semester |
| `assignments` | `idx_assignments_class` | List assignments for class |
| `assignment_grades` | `idx_assignment_grades_student` | Get student's grades |
| `attendance_records` | `idx_attendance_class_date` | Class attendance on date |
| `attendance_records` | `idx_attendance_date` | All attendance on date |
| `timetable_slots` | `idx_timetable_class` | Class schedule |
| `timetable_slots` | `idx_timetable_teacher` | Teacher schedule |
| `invoices` | `idx_invoices_status` | Filter by payment status |
| `invoices` | `idx_invoices_due_date` | Overdue invoice queries |
| `notifications` | `idx_notifications_recipient` | User's unread notifications |

### Composite Indexes for Multi-Tenant Queries

All queries must filter by `school_id` first. The following composite indexes ensure this:

```sql
CREATE INDEX idx_classes_school_level ON classes(school_id, level_key, year_name);
CREATE INDEX idx_notes_school_student ON notes(school_id, student_id, semester);
CREATE INDEX idx_attendance_school_date ON attendance_records(school_id, date);
```

---

## Row-Level Security

### Enable RLS on all tables

```sql
-- Run after table creation
ALTER TABLE classes ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE matieres ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignment_grades ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE timetable_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE fee_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE admission_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE parent_student ENABLE ROW LEVEL SECURITY;
```

### Create policies

```sql
-- Generic policy for all tables (example for classes)
CREATE POLICY school_isolation ON classes
    USING (school_id = current_setting('app.current_school_id')::uuid);

-- Repeat for every table:
CREATE POLICY school_isolation ON students
    USING (school_id = current_setting('app.current_school_id')::uuid);

CREATE POLICY school_isolation ON matieres
    USING (school_id = current_setting('app.current_school_id')::uuid);

-- ... (same pattern for all tables)
```

### Set session variable (in Python)

```python
from sqlalchemy import text

async def set_school_context(session, school_id: str):
    await session.execute(
        text("SET app.current_school_id = :school_id"),
        {"school_id": str(school_id)}
    )
```

This is called automatically by the tenant middleware on every request.

---

## Migrations

### Setup

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Generate a migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View migration history
alembic history
```

### Migration Naming Convention

```
001_create_schools_and_users.py
002_create_classes_and_students.py
003_create_subjects_and_grades.py
004_create_assignments.py
005_create_attendance.py
006_create_timetable.py
007_create_portals.py
008_create_invoices.py
009_create_admissions.py
010_create_notifications.py
011_create_audit_logs.py
012_seed_moroccan_curriculum.py
013_enable_rls.py
```

---

## Seed Data

### Super Admin

Created by `app/seed.py`:

```python
# Default super admin
{
    "email": "superadmin@mainpixel.ma",
    "password": "ChangeMe123!",  # Change immediately
    "role": "super_admin",
    "full_name": "Platform Admin"
}
```

### Moroccan Curriculum

Seeded per-school when a school first accesses the subjects endpoint. Includes:

- **Primary (1-6)**: Arabic, French, Math, SVT, History-Geo, etc.
- **Middle School (1-3)**: Arabic, French, Math, Physics, SVT, History-Geo, IT
- **Lycée Tronc Commun (1)**: Full subject set for Science/Letters/Technology
- **1BAC (2)**: 8 branches (SM, SVT, PC, Letters, Econ, Electric, Mechanical)
- **2BAC (3)**: 8 branches with specific coefficients

See `backend/app/services/grade_service.py` for the complete seed data.

### School-Level Seeding

When a new school registers, seed:
1. Default `levels_config` (from the registration request or Moroccan defaults)
2. Moroccan curriculum subjects (if not already seeded for that school)
3. No classes or students (school admin creates these)
