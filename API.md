# API Reference — MainPixel

Base URL: `http://localhost:8000/api`

All endpoints require JWT authentication unless marked as 🔓 **public**.

---

## Table of Contents

- [Common](#common)
- [Auth](#auth)
- [Schools](#schools)
- [Classes](#classes)
- [Students](#students)
- [Subjects](#subjects)
- [Grades](#grades)
- [Assignments](#assignments)
- [Attendance](#attendance)
- [Timetable](#timetable)
- [Parent Portal](#parent-portal)
- [Student Portal](#student-portal)
- [Invoices](#invoices)
- [Admissions](#admissions)
- [Notifications](#notifications)
- [Dashboard](#dashboard)
- [Export](#export)
- [Config](#config)

---

## Common

### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Pagination

All list endpoints support cursor-based pagination:

```
GET /api/classes?page=1&per_page=20
```

Response includes:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

### Error Responses

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient role) |
| 404 | Not found |
| 409 | Conflict (duplicate) |
| 422 | Validation error (details in response) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### Filtering

Most list endpoints support query parameter filtering:

```
GET /api/students?class_id=abc-123&search=ahmed
GET /api/attendance?classe_id=abc-123&date=2026-08-29
GET /api/invoices?status=overdue
```

---

## Auth

### 🔓 POST /auth/login

Authenticate a user and receive JWT tokens.

**Request:**

```json
{
  "email": "admin@ecole-x.ma",
  "password": "securepassword"
}
```

**Response (200):**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "admin@ecole-x.ma",
    "full_name": "Mohammed Alami",
    "role": "school_admin",
    "school_id": "uuid"
  }
}
```

**Errors:**
- 401: Invalid credentials
- 429: Too many attempts (5 per 15 min per IP + email)

---

### 🔓 POST /auth/refresh

Get a new access token using a refresh token.

**Request:**

```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:**
- 401: Invalid or expired refresh token

---

### POST /auth/logout

Invalidate the current refresh token.

**Headers:** `Authorization: Bearer <access_token>`

**Response (204):** No content

---

### POST /auth/forgot-password

Request a password reset email.

**Request:**

```json
{
  "email": "admin@ecole-x.ma"
}
```

**Response (200):**

```json
{
  "message": "If the email exists, a reset link has been sent"
}
```

---

### 🔓 POST /auth/reset-password

Reset password using the token from email.

**Request:**

```json
{
  "token": "reset-token-from-email",
  "new_password": "newsecurepassword"
}
```

**Response (200):**

```json
{
  "message": "Password reset successful"
}
```

---

## Schools

### 🔓 POST /schools/register

Register a new school and create the first admin account.

**Request:**

```json
{
  "school_name": "École Al Amal",
  "admin_email": "admin@alamal.ma",
  "admin_password": "securepassword",
  "admin_full_name": "Mohammed Alami",
  "levels_config": {
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
}
```

**Response (201):**

```json
{
  "school": {
    "id": "uuid",
    "name": "École Al Amal",
    "slug": "ecole-alamal",
    "plan": "trial"
  },
  "admin": {
    "id": "uuid",
    "email": "admin@alamal.ma",
    "role": "school_admin"
  }
}
```

**Errors:**
- 409: School slug already exists
- 422: Validation error

---

### GET /schools/{school_id}

Get school details.

**Roles:** super_admin, school_admin

**Response (200):**

```json
{
  "id": "uuid",
  "name": "École Al Amal",
  "slug": "ecole-alamal",
  "plan": "standard",
  "levels_config": { ... },
  "status": "active",
  "created_at": "2026-08-29T10:00:00Z"
}
```

---

## Classes

### GET /classes

List all classes in the current school.

**Roles:** school_admin, teacher

**Query Parameters:**
- `level_key` (optional): Filter by level (primary, middle, lycee)
- `year_name` (optional): Filter by year
- `search` (optional): Search by name

**Response (200):**

```json
[
  {
    "id": "uuid",
    "level_key": "middle",
    "level_name": "Collège",
    "year_name": "3",
    "name": "3ème A",
    "branch": "",
    "student_count": 35,
    "academic_year": "2025-2026",
    "created_at": "2026-08-29T10:00:00Z"
  }
]
```

---

### POST /classes

Create a new class.

**Roles:** school_admin

**Request:**

```json
{
  "level_key": "middle",
  "year_name": "3",
  "name": "3ème A",
  "branch": "",
  "academic_year": "2025-2026"
}
```

**Response (201):** Created class object

**Errors:**
- 409: Class with same level/year/name/branch already exists

---

### GET /classes/{class_id}

Get a single class with details.

**Roles:** school_admin, teacher

---

### PUT /classes/{class_id}

Update a class.

**Roles:** school_admin

**Request:**

```json
{
  "name": "3ème B",
  "academic_year": "2025-2026"
}
```

**Response (200):** Updated class object

---

### DELETE /classes/{class_id}

Delete a class and all its students/grades.

**Roles:** school_admin

**Response (204):** No content

**Warning:** This is a hard delete. Use with caution.

---

### GET /classes/{class_id}/students

List students in a class.

**Roles:** school_admin, teacher

**Query Parameters:**
- `search` (optional): Filter by name or code_massar
- `page`, `per_page`: Pagination

**Response (200):**

```json
[
  {
    "id": "uuid",
    "full_name": "Ahmed Ben Ali",
    "code_massar": "M1234567890",
    "birth_date": "2010-05-15",
    "sexe": "M",
    "sort_order": 0
  }
]
```

---

### POST /classes/{class_id}/students

Add a student to a class.

**Roles:** school_admin

**Request:**

```json
{
  "full_name": "Ahmed Ben Ali",
  "code_massar": "M1234567890",
  "birth_date": "2010-05-15",
  "sexe": "M",
  "address": "123 Rue Mohammed V, Rabat",
  "father_name": "Ali Ben Ali",
  "mother_name": "Fatima Zahra",
  "comment": ""
}
```

**Response (201):** Created student object

**Errors:**
- 409: code_massar already exists
- 400: Class already has 60 students (max)

---

### POST /classes/{class_id}/students/import

Import students from a CSV file.

**Roles:** school_admin

**Request:** `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| file | CSV file | Yes |

**CSV Format:**

```csv
Nom complet,Numero scolaire,Date de naissance,Notes
Ahmed Ben Ali,M1234567890,2010-05-15,
Fatima Zahra,M9876543210,2010-03-20,Good student
```

**Response (200):**

```json
{
  "imported": 25,
  "skipped": 3,
  "errors": ["Row 15: code_massar already exists"]
}
```

---

## Students

### GET /students/{student_id}

Get student details.

**Roles:** school_admin, teacher

---

### PUT /students/{student_id}

Update a student.

**Roles:** school_admin

**Request:**

```json
{
  "full_name": "Ahmed Ben Ali (updated)",
  "birth_date": "2010-05-15"
}
```

---

### DELETE /students/{student_id}

Delete a student.

**Roles:** school_admin

**Response (204):** No content

---

## Subjects

### GET /subjects

List subjects for the school.

**Roles:** school_admin, teacher

**Query Parameters:**
- `level_key` (required)
- `year_name` (required)
- `branch` (optional): Filter by branch

**Response (200):**

```json
[
  {
    "id": "uuid",
    "name": "Mathematiques",
    "coefficient": 4.0,
    "level_key": "lycee",
    "year_name": "1",
    "branch": "Tronc Commun Scientifique"
  }
]
```

---

### POST /subjects

Add a subject.

**Roles:** school_admin

**Request:**

```json
{
  "name": "Informatique",
  "coefficient": 2.0,
  "level_key": "lycee",
  "year_name": "1",
  "branch": "Tronc Commun Scientifique"
}
```

---

### POST /subjects/seed

Seed Moroccan curriculum subjects for all levels.

**Roles:** school_admin

**Response (200):**

```json
{
  "seeded": 145,
  "message": "145 subjects seeded"
}
```

---

### PUT /subjects/{subject_id}

Update a subject.

**Roles:** school_admin

---

### DELETE /subjects/{subject_id}

Delete a subject.

**Roles:** school_admin

---

## Grades

### GET /grades/{student_id}

Get a student's grades for a semester.

**Roles:** school_admin, teacher, parent (own child), student (self)

**Query Parameters:**
- `semester` (required): 1 or 2

**Response (200):**

```json
{
  "student_id": "uuid",
  "semester": 1,
  "grades": [
    {
      "matiere_id": "uuid",
      "matiere_name": "Mathematiques",
      "coefficient": 4.0,
      "valeur": 15.5
    }
  ],
  "average": 14.25
}
```

---

### PUT /grades/{student_id}

Save/update grades for a student's semester.

**Roles:** school_admin, teacher

**Request:**

```json
{
  "semester": 1,
  "grades": [
    { "matiere_id": "uuid", "valeur": 15.5 },
    { "matiere_id": "uuid", "valeur": 12.0 }
  ]
}
```

**Response (200):** Updated grades

---

### GET /grades/{student_id}/averages

Calculate semester and year averages.

**Roles:** school_admin, teacher, parent (own child), student (self)

**Response (200):**

```json
{
  "student_id": "uuid",
  "semester_1_average": 14.25,
  "semester_2_average": 13.80,
  "year_average": 14.03
}
```

---

## Assignments

### GET /assignments

List assignments for a class/subject/semester.

**Roles:** school_admin, teacher

**Query Parameters:**
- `class_id` (required)
- `matiere_id` (required)
- `semester` (required)

**Response (200):**

```json
[
  {
    "id": "uuid",
    "title": "Contrôle 1",
    "coefficient": 1.0,
    "date": "2026-09-15",
    "created_at": "2026-08-29T10:00:00Z"
  }
]
```

---

### POST /assignments

Create an assignment.

**Roles:** school_admin, teacher

**Request:**

```json
{
  "class_id": "uuid",
  "matiere_id": "uuid",
  "semester": 1,
  "title": "Contrôle 1",
  "coefficient": 1.0,
  "date": "2026-09-15"
}
```

---

### PUT /assignments/{assignment_id}

Update an assignment.

**Roles:** school_admin, teacher

---

### DELETE /assignments/{assignment_id}

Delete an assignment and its grades.

**Roles:** school_admin, teacher

---

### GET /assignments/{assignment_id}/grades

Get grades for an assignment.

**Roles:** school_admin, teacher

**Response (200):**

```json
{
  "assignment_id": "uuid",
  "grades": {
    "student-uuid-1": 15.5,
    "student-uuid-2": 12.0,
    "student-uuid-3": null
  }
}
```

---

### POST /assignments/{assignment_id}/grades

Save grades for an assignment (bulk).

**Roles:** school_admin, teacher

**Request:**

```json
{
  "grades": {
    "student-uuid-1": 15.5,
    "student-uuid-2": 12.0,
    "student-uuid-3": 18.0
  }
}
```

**Response (200):**

```json
{
  "saved": 3,
  "averages": {
    "student-uuid-1": 15.5,
    "student-uuid-2": 12.0,
    "student-uuid-3": 18.0
  }
}
```

---

### POST /assignments/sync

Sync assignment averages to final notes.

**Roles:** school_admin

**Request:**

```json
{
  "class_id": "uuid",
  "matiere_id": "uuid",
  "semester": 1
}
```

**Response (200):**

```json
{
  "synced": 35,
  "message": "Averages synced to notes for 35 students"
}
```

---

## Attendance

### POST /attendance

Record attendance for a class (bulk).

**Roles:** school_admin, teacher

**Request:**

```json
{
  "classe_id": "uuid",
  "date": "2026-08-29",
  "period": "morning",
  "records": [
    { "student_id": "uuid", "status": "present" },
    { "student_id": "uuid", "status": "absent" },
    { "student_id": "uuid", "status": "late", "justification_note": "Bus delay" },
    { "student_id": "uuid", "status": "excused", "justification_note": "Medical certificate" }
  ]
}
```

**Status enum:** `present`, `absent`, `late`, `excused`

**Response (201):**

```json
{
  "recorded": 35,
  "absences": 2,
  "warnings": ["Student X has 4 absences this month"]
}
```

**Errors:**
- 409: Attendance already recorded for this class/date/period

---

### GET /attendance

List attendance records.

**Roles:** school_admin, teacher (own classes), parent (own child), student (self)

**Query Parameters:**
- `classe_id` (required for admin/teacher)
- `student_id` (required for parent/student)
- `date` (optional): Specific date
- `start_date`, `end_date` (optional): Date range
- `period` (optional): Filter by period

**Response (200):**

```json
[
  {
    "id": "uuid",
    "student_id": "uuid",
    "student_name": "Ahmed Ben Ali",
    "classe_id": "uuid",
    "date": "2026-08-29",
    "status": "present",
    "period": "morning",
    "recorded_by": "uuid",
    "justification_note": null
  }
]
```

---

### PATCH /attendance/{id}

Update an attendance record (justify absence).

**Roles:** school_admin

**Request:**

```json
{
  "status": "excused",
  "justification_note": "Medical certificate uploaded"
}
```

---

### GET /attendance/stats

Get attendance statistics.

**Roles:** school_admin, teacher

**Query Parameters:**
- `classe_id` (required)
- `period` (optional): Filter by period
- `start_date`, `end_date` (optional): Date range

**Response (200):**

```json
{
  "total_days": 20,
  "present_rate": 92.5,
  "absent_rate": 4.2,
  "late_rate": 2.1,
  "excused_rate": 1.2,
  "students": [
    {
      "student_id": "uuid",
      "student_name": "Ahmed Ben Ali",
      "present": 18,
      "absent": 1,
      "late": 1,
      "excused": 0,
      "rate": 90.0
    }
  ]
}
```

---

## Timetable

### POST /timetable/slots

Create or update timetable slots (bulk).

**Roles:** school_admin

**Request:**

```json
{
  "classe_id": "uuid",
  "academic_year": "2025-2026",
  "slots": [
    {
      "day_of_week": 0,
      "start_time": "08:00",
      "end_time": "09:00",
      "matiere_id": "uuid",
      "teacher_id": "uuid",
      "room": "Salle 1"
    }
  ]
}
```

**Errors:**
- 409: Teacher conflict (same teacher at overlapping time)
- 409: Room conflict (same room at overlapping time)

---

### GET /timetable

Get timetable for a class or teacher.

**Roles:** school_admin, teacher, parent (own child), student (self)

**Query Parameters:**
- `classe_id` (optional): Class schedule
- `teacher_id` (optional): Teacher schedule

**Response (200):**

```json
{
  "classe_id": "uuid",
  "academic_year": "2025-2026",
  "slots": [
    {
      "id": "uuid",
      "day_of_week": 0,
      "day_name": "Monday",
      "start_time": "08:00",
      "end_time": "09:00",
      "matiere": { "id": "uuid", "name": "Mathematiques" },
      "teacher": { "id": "uuid", "full_name": "Mme. Khadija" },
      "room": "Salle 1"
    }
  ]
}
```

---

## Parent Portal

### GET /parent/children

List children linked to the current parent.

**Roles:** parent

**Response (200):**

```json
[
  {
    "student_id": "uuid",
    "full_name": "Ahmed Ben Ali",
    "class_name": "3ème A",
    "level_name": "Collège",
    "year_name": "3"
  }
]
```

---

### GET /parent/children/{student_id}/grades

Get a child's grades.

**Roles:** parent

**Query Parameters:**
- `semester` (required)

**Response:** Same as `GET /grades/{student_id}`

**Security:** Verifies `student_id` is actually linked to the parent via `parent_student` table.

---

### GET /parent/children/{student_id}/attendance

Get a child's attendance.

**Roles:** parent

**Query Parameters:**
- `start_date`, `end_date` (optional)

**Response:** Same as `GET /attendance?student_id=...`

---

### GET /parent/children/{student_id}/timetable

Get a child's timetable.

**Roles:** parent

**Response:** Same as `GET /timetable?classe_id=...`

---

### POST /parent/children/{student_id}/attendance-justification

Upload an absence justification.

**Roles:** parent

**Request:** `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| attendance_id | UUID | Yes |
| file | PDF/JPG/PNG | Yes |
| note | text | No |

**Response (201):**

```json
{
  "message": "Justification uploaded successfully"
}
```

---

## Student Portal

### GET /student/grades

Get own grades.

**Roles:** student

**Query Parameters:**
- `semester` (required)

---

### GET /student/attendance

Get own attendance.

**Roles:** student

---

### GET /student/timetable

Get own timetable.

**Roles:** student

---

## Invoices

### GET /invoices

List invoices.

**Roles:** school_admin, parent (own only)

**Query Parameters:**
- `student_id` (optional): Filter by student
- `status` (optional): Filter by status (pending, paid, overdue, cancelled)
- `level_key` (optional): Filter by level

**Response (200):**

```json
[
  {
    "id": "uuid",
    "student_id": "uuid",
    "student_name": "Ahmed Ben Ali",
    "fee_plan_name": "Frais de scolarité - Mensuel",
    "amount_due": 500.00,
    "due_date": "2026-09-30",
    "status": "pending",
    "paid_at": null,
    "payment_method": null
  }
]
```

---

### POST /invoices/generate

Bulk generate invoices for a class/level.

**Roles:** school_admin

**Request:**

```json
{
  "fee_plan_id": "uuid",
  "class_id": "uuid",
  "due_date": "2026-09-30"
}
```

**Response (200):**

```json
{
  "generated": 35,
  "total_amount": 17500.00
}
```

---

### PATCH /invoices/{id}/mark-paid

Mark an invoice as paid.

**Roles:** school_admin

**Request:**

```json
{
  "payment_method": "cash",
  "amount_paid": 500.00
}
```

**Response (200):** Updated invoice object

**Audit:** All amount changes are logged in `audit_logs`.

---

### GET /invoices/overdue

List overdue invoices.

**Roles:** school_admin

**Response (200):** Array of overdue invoice objects

---

## Admissions

### 🔓 POST /admissions/apply

Submit an admission application (public endpoint).

**Request:**

```json
{
  "applicant_name": "Sara Ben Ali",
  "birth_date": "2016-09-15",
  "desired_level": "primary",
  "desired_year": "1",
  "parent_name": "Ahmed Ben Ali",
  "parent_phone": "+212612345678",
  "parent_email": "ahmed@example.com",
  "documents": []
}
```

**Response (201):**

```json
{
  "id": "uuid",
  "status": "submitted",
  "message": "Application submitted successfully. We will contact you."
}
```

**Protection:** CAPTCHA required (Cloudflare Turnstile or hCaptcha).

---

### GET /admissions

List admission applications.

**Roles:** school_admin

**Query Parameters:**
- `status` (optional): Filter by status

**Response (200):**

```json
[
  {
    "id": "uuid",
    "applicant_name": "Sara Ben Ali",
    "birth_date": "2016-09-15",
    "desired_level": "primary",
    "parent_name": "Ahmed Ben Ali",
    "parent_phone": "+212612345678",
    "status": "submitted",
    "submitted_at": "2026-08-29T10:00:00Z"
  }
]
```

---

### PATCH /admissions/{id}/status

Update an admission application status.

**Roles:** school_admin

**Request:**

```json
{
  "status": "accepted",
  "class_id": "uuid"
}
```

**Status values:** `submitted`, `under_review`, `accepted`, `rejected`, `waitlisted`

**When status = "accepted":**
Single transaction:
1. Create student record
2. Assign to class (if class_id provided)
3. Find or create parent user account
4. Create parent_student link
5. Send acceptance notification

---

## Notifications

### GET /notifications

List notifications for the current user.

**Roles:** all

**Query Parameters:**
- `is_read` (optional): Filter by read status
- `type` (optional): Filter by notification type

**Response (200):**

```json
[
  {
    "id": "uuid",
    "type": "grade_published",
    "title": "New grades available",
    "body": "Your child Ahmed has new grades in Mathematics.",
    "channel": "in_app",
    "is_read": false,
    "sent_at": "2026-08-29T10:00:00Z"
  }
]
```

---

### PATCH /notifications/{id}/read

Mark a notification as read.

**Roles:** all

**Response (204):** No content

---

### PATCH /notifications/read-all

Mark all notifications as read.

**Roles:** all

**Response (204):** No content

---

## Dashboard

### GET /dashboard/overview

Get school overview statistics.

**Roles:** school_admin

**Response (200):**

```json
{
  "total_students": 450,
  "total_teachers": 25,
  "total_classes": 18,
  "attendance_rate_today": 94.5,
  "pending_admissions": 12,
  "overdue_invoices": 8,
  "recent_notifications": 5
}
```

---

### GET /dashboard/grades-distribution

Get grade distribution for a class.

**Roles:** school_admin, teacher

**Query Parameters:**
- `class_id` (required)
- `semester` (required)

**Response (200):**

```json
{
  "class_id": "uuid",
  "semester": 1,
  "distribution": {
    "0-4": 2,
    "4-8": 5,
    "8-12": 12,
    "12-16": 10,
    "16-20": 6
  },
  "average": 12.5,
  "median": 12.8,
  "pass_rate": 78.5
}
```

---

### GET /dashboard/attendance-trend

Get attendance trend over time.

**Roles:** school_admin

**Query Parameters:**
- `period` (optional): 7d, 30d, 90d (default: 30d)

**Response (200):**

```json
{
  "period": "30d",
  "daily_rates": [
    { "date": "2026-08-01", "rate": 95.2 },
    { "date": "2026-08-02", "rate": 93.8 }
  ],
  "overall_rate": 94.1
}
```

---

### GET /dashboard/financial-summary

Get financial overview.

**Roles:** school_admin

**Response (200):**

```json
{
  "total_expected": 225000.00,
  "total_paid": 180000.00,
  "total_overdue": 30000.00,
  "paid_rate": 80.0,
  "overdue_count": 15
}
```

---

## Export

### GET /export/{class_id}/html

Export class report as HTML.

**Roles:** school_admin, teacher

**Response:** HTML file download

---

### GET /export/{class_id}/pdf

Export class report as PDF.

**Roles:** school_admin, teacher

**Response:** PDF file download

---

### GET /export/{student_id}/certificate

Generate a school certificate for a student.

**Roles:** school_admin

**Response:** HTML file download

---

### GET /export/{class_id}/students-csv

Export student list as CSV.

**Roles:** school_admin, teacher

**Response:** CSV file download

---

### POST /export/backup

Export full school data as ZIP.

**Roles:** school_admin

**Response (200):**

```json
{
  "path": "/backups/school_20260829.zip",
  "size_mb": 12.5
}
```

---

## Config

### GET /config

Get school configuration.

**Roles:** school_admin

**Response (200):**

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

### PUT /config

Update school configuration.

**Roles:** school_admin

**Request:**

```json
{
  "levels": {
    "primary": "Primaire",
    "middle": "Collège",
    "lycee": "Lycée"
  }
}
```

---

### GET /config/audit-logs

Get audit logs for the school.

**Roles:** school_admin

**Query Parameters:**
- `entity_type` (optional): Filter by entity type
- `action` (optional): Filter by action
- `start_date`, `end_date` (optional): Date range

**Response (200):**

```json
[
  {
    "id": "uuid",
    "user_name": "admin@ecole-x.ma",
    "action": "create",
    "entity_type": "student",
    "entity_id": "uuid",
    "details": "Added student Ahmed Ben Ali",
    "created_at": "2026-08-29T10:00:00Z"
  }
]
```
