# Transit Nexus — Full Multi-Role Platform (Django)

A Django clone of the full Transit Nexus platform: **Admin**, **College**,
**Trainer**, **Company**, and **Student** dashboards, all backed by a real
database — no static/dummy HTML.

The site's home page (`/`) sends every visitor to the dashboard that matches
their role. The **Admin Dashboard** is the platform's overall landing page —
if a logged-in account has no other role profile attached, it defaults there.

## Demo login accounts
Run `python manage.py seed_data` and `python manage.py seed_portal` (see
Setup below) to create these:

| Role     | Username          | Password      | Lands on            |
|----------|-------------------|---------------|----------------------|
| Admin    | `Transit_admin`    | `admin123`    | `/admin-dashboard/`  |
| College  | `college_admin`   | `college123`  | `/college-dashboard/`|
| Trainer  | `trainer_srinath` | `trainer123`  | `/trainer-dashboard/`|
| Company  | `company_hr`      | `company123`  | `/company-dashboard/`|
| Student  | `ananya`          | `student123`  | `/student-dashboard/`|

## What's inside
- **Django auth** — login/logout, session-protected pages, role-aware redirect
  after login (each account type goes straight to its own dashboard)
- **Two apps:**
  - `dashboard` — the Student experience: dashboard + 13 working sub-pages
    (profile, courses, live classes, attendance, assessments, results & reports,
    assignments, certificates, learning path, skill progress, messages,
    calendar, payments)
  - `portal` — Admin, College, Trainer, and Company dashboards, each with a
    full set of working sub-pages (see below) — every sidebar link is real,
    nothing is a placeholder
- **Everything is dynamic** — every number, table row, chart and donut is
  computed from the database in the relevant `views.py`, nothing is hard-coded
  in the templates
- **Charts** — Chart.js line charts fed by real query data (attendance trends,
  score trends, department performance trends, etc.)
- **Admin panel** — manage all data for every role at `/admin/`
- **Seed commands** — `seed_data` (student) and `seed_portal` (the other four
  roles) load realistic demo data matching the reference screenshots

## Every sidebar page, by role

**Admin** — Dashboard, Colleges Management, Students Management, Training
Programs, Assessments, Interviews, Projects, Syllabus Management, Schedules,
Attendance, Payments & Invoices, Reports & Analytics, Support & Issues,
Users & Roles, Communications, Settings

**College** — Dashboard, Department Overview, Student Performance,
Assessments, Attendance, Training Programs, Placements, Reports & Analytics,
Faculty Performance, Syllabus Coverage, Notifications, Settings

**Trainer** — Dashboard, My Batches, Attendance, Assessments, Assignments,
Student Performance, Question Bank, Reports, Training Calendar, Settings

**Company** — Dashboard, Search Students (with filters), Shortlisted
Candidates, Interviews, Job Drives, Offers, Reports, Company Profile, Settings

**Student** — Dashboard, My Profile, My Courses, Live Classes, My Attendance,
Assessments, Results & Reports, Assignments, Certificates, Learning Path,
Skill Progress, Messages, Calendar, My Payments

## Setup

```bash
# 1. Create & activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure PostgreSQL (PowerShell example)
$env:POSTGRES_DB = "transit_nexus"
$env:POSTGRES_USER = "postgres"
$env:POSTGRES_PASSWORD = "your-postgres-password"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"

# 4. Run migrations
python manage.py migrate

# 5. Load demo data
python manage.py seed_data      # creates the student account (ananya)
python manage.py seed_portal    # creates admin / college / trainer / company accounts

# 6. (optional) create your own superuser for /admin/
python manage.py createsuperuser

# 7. Run the server
python manage.py runserver
```

If `POSTGRES_DB` is not set, the project uses the local SQLite database. Create
the PostgreSQL database first with `CREATE DATABASE transit_nexus;`, then run
the migration and seed commands above.

## Controlled user access

Create accounts as pending so they cannot log in until an administrator
approves them:

```bash
python manage.py create_pending_user student_0501 student-pass-123 student --first-name "New" --last-name "Student" --email new.student@example.com
python manage.py create_pending_user college_0101 college-pass-123 college --first-name "College" --last-name "Admin" --email college@example.com
python manage.py create_pending_user trainer_0101 trainer-pass-123 trainer --first-name "Trainer" --last-name "User" --email trainer@example.com
python manage.py create_pending_user company_0101 company-pass-123 company --first-name "Company" --last-name "HR" --email hr@company.example.com
```

Sign in to `/admin/` with your superuser, open **Users**, select the account,
enable **Active**, and save. Only then can that user log in. The bulk demo
accounts are already active for testing; newly created pending accounts are
inactive by default.

Visit **http://127.0.0.1:8000/** — you'll be redirected to `/login/`.
Log in with any of the accounts in the table above.

## Project structure
```
transit_nexus/
├── manage.py
├── requirements.txt
├── transit_nexus/          # project settings/urls
└── dashboard/               # the app
    ├── models.py            # DB schema
    ├── views.py              # every page's logic / aggregation
    ├── urls.py
    ├── admin.py
    ├── management/commands/seed_data.py
    ├── templates/dashboard/
    │   ├── base.html
    │   ├── _page_base.html    # shared shell (sidebar + topbar + content block)
    │   ├── _sidebar.html      # shared sidebar, handles active-link state
    │   ├── _topbar.html       # shared topbar, handles unread message badge
    │   ├── login.html
    │   ├── student_dashboard.html
    │   ├── profile.html
    │   ├── courses.html
    │   ├── live_classes.html
    │   ├── attendance.html
    │   ├── assessments.html
    │   ├── results_reports.html
    │   ├── assignments.html
    │   ├── certificates.html
    │   ├── learning_path.html
    │   ├── skill_progress.html
    │   ├── messages.html
    │   ├── calendar.html
    │   └── payments.html
    └── static/dashboard/
        ├── css/style.css
        └── js/script.js
portal/                        # Admin, College, Trainer, Company
├── models.py                  # ~35 models across all 4 roles
├── views.py                   # every dashboard + sub-page's logic
├── urls.py
├── admin.py
├── management/commands/seed_portal.py
└── templates/portal/
    ├── _page_base.html         # shared shell (sidebar + topbar + content)
    ├── _sidebar.html           # generic sidebar, driven by nav_items context
    ├── _topbar.html
    ├── admin_dashboard.html + 15 admin sub-page templates
    ├── college_dashboard.html + 11 college sub-page templates
    ├── trainer_dashboard.html + 9 trainer sub-page templates
    └── company_dashboard.html + 8 company sub-page templates
```

## Customizing the data
Everything shown on the dashboard comes from the database — nothing is
hard-coded in the template. To change what's displayed:
- Edit rows via **Django admin** (`/admin/`), or
- Edit `dashboard/management/commands/seed_data.py` and re-run
  `python manage.py seed_data` (it wipes and reloads that student's data).

To add a **new student**, create a `User` + `StudentProfile`, then add their
`Enrollment`, `AttendanceRecord`, `Assessment`, etc. rows (via admin or a
script) — the same dashboard view will render correctly for them.

## Next steps (if you want more dashboards)
This covers the **Student Dashboard** only, per your request. The same
Django project can be extended with additional apps/views for the
**College Admin**, **Trainer**, **Company**, and **Super Admin** dashboards
shown in your reference images — just ask and I'll add them the same way
(models + views + templates + CSS), reusing this sidebar/topbar/card system.
