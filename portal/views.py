import csv
import io
import json
import time
from datetime import date
from functools import wraps
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import OperationalError, connections, transaction
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone

from .models import (
    AdminProfile, PartnerCollege, SupportTicket, AdminProject, SyllabusUpdate,
    TopProgram, AdminScheduleItem,
    CollegeProfile, Department, CollegeTrendPoint, CollegeQuickReport,
    TrainerProfile, Batch, TrainerAssessment, PendingTask, TrainerTrendPoint,
    CompanyProfile, Candidate, CompanyInterview,
    AdminStudentRecord, AdminAttendanceSummary, AdminInvoice, Announcement,
    CollegeStudent, CollegeAssessment, CollegeProgram, PlacementRecord,
    Faculty, SyllabusCoverage, CollegeNotification,
    BatchAttendanceEntry, TrainerAssignment, TrainerStudent, QuestionBankItem,
    TrainerCalendarEvent, TrainerAvailability, OnlineTest, OnlineTestQuestion,
    OnlineTestAttempt, OnlineTestAnswer, JobDrive, Offer,
)
from .forms import (
    CollegeAssessmentForm, CollegeInvoiceForm, CollegeProgramForm, CollegeQuickReportForm,
    CollegeInvoiceForm, CollegeQuickReportForm, CollegeStudentAccountForm, CollegeStudentForm,
    DepartmentAttendanceForm, FacultyForm, OnlineTestForm, PlacementRecordForm, SyllabusCoverageForm,
)
from dashboard.models import StudentProfile


ADMIN_NAV = [
    ("fa-solid fa-house", "Platform Dashboard", "admin_dashboard"),
    ("fa-solid fa-building-columns", "Colleges", "admin_colleges"),
    ("fa-solid fa-chalkboard-user", "Trainers", "admin_trainers"),
    ("fa-solid fa-users-gear", "Users & Roles", "admin_users"),
    ("fa-solid fa-file-import", "Bulk Import", "bulk_import"),
    ("fa-solid fa-headset", "Support & Issues", "admin_support"),
    ("fa-solid fa-bullhorn", "Communications", "admin_communications"),
    ("fa-solid fa-gear", "Settings", "admin_settings"),
]

COLLEGE_NAV = [
    ("fa-solid fa-house", "Dashboard", "college_dashboard"),
    ("fa-solid fa-sitemap", "Department Overview", "college_departments"),
    ("fa-solid fa-user-graduate", "Student Performance", "college_students"),
    ("fa-solid fa-clipboard-list", "Assessments", "college_assessments"),
    ("fa-solid fa-calendar-check", "Attendance", "college_attendance"),
    ("fa-solid fa-chalkboard-user", "Training Programs", "college_programs"),
    ("fa-solid fa-file-invoice-dollar", "Payments", "college_payments"),
    ("fa-solid fa-briefcase", "Placements", "college_placements"),
    ("fa-solid fa-chart-line", "Reports & Analytics", "college_reports"),
    ("fa-solid fa-chalkboard-teacher", "Faculty Performance", "college_faculty"),
    ("fa-solid fa-book-open", "Syllabus Coverage", "college_syllabus"),
    ("fa-regular fa-bell", "Notifications", "college_notifications"),
    ("fa-solid fa-gear", "Settings", "college_settings"),
]

TRAINER_NAV = [
    ("fa-solid fa-house", "Dashboard", "trainer_dashboard"),
    ("fa-solid fa-people-group", "My Batches", "trainer_batches"),
    ("fa-solid fa-calendar-check", "Attendance", "trainer_attendance"),
    ("fa-solid fa-clipboard-list", "Assessments", "trainer_assessments"),
    ("fa-solid fa-list-check", "Assignments", "trainer_assignments"),
    ("fa-solid fa-chart-line", "Student Performance", "trainer_students"),
    ("fa-solid fa-database", "Question Bank", "trainer_question_bank"),
    ("fa-solid fa-file-lines", "Reports", "trainer_reports"),
    ("fa-solid fa-calendar-days", "Training Calendar", "trainer_calendar"),
    ("fa-solid fa-gear", "Settings", "trainer_settings"),
]

COMPANY_NAV = [
    ("fa-solid fa-house", "Dashboard", "company_dashboard"),
    ("fa-solid fa-magnifying-glass", "Search Students", "company_search"),
    ("fa-solid fa-star", "Shortlisted Candidates", "company_shortlisted"),
    ("fa-solid fa-people-arrows", "Interviews", "company_interviews"),
    ("fa-solid fa-car-side", "Job Drives", "company_drives"),
    ("fa-solid fa-file-signature", "Offers", "company_offers"),
    ("fa-solid fa-chart-line", "Reports", "company_reports"),
    ("fa-solid fa-building", "Company Profile", "company_profile"),
    ("fa-solid fa-gear", "Settings", "company_settings"),
]


def _nav_context(nav_list, active_label, role_title, role_tagline):
    return {
        "nav_items": [
            {"icon": icon, "label": label, "url": url, "active": label == active_label}
            for icon, label, url in nav_list
        ],
        "role_title": role_title,
        "role_tagline": role_tagline,
    }


def _page_ctx(profile, nav_list, active_label, title, subtitle, role_label, **extra):
    ctx = {
        "profile": profile,
        "page_title": title,
        "page_subtitle": subtitle,
        "user_role_label": role_label,
        **_nav_context(nav_list, active_label, "TRANSIT NEXUS", "LEARN · ASSESS · GROW"),
    }
    ctx.update(extra)
    return ctx


def platform_admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_staff or hasattr(request.user, "admin_profile")):
            return HttpResponseForbidden("Platform administrator access is required.")
        return view_func(request, *args, **kwargs)
    return wrapped


def college_account_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_staff or hasattr(request.user, "admin_profile") or not hasattr(request.user, "college_profile"):
            return HttpResponseForbidden("College account access is required.")
        return view_func(request, *args, **kwargs)
    return wrapped


def trainer_account_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if (
            request.user.is_staff
            or hasattr(request.user, "admin_profile")
            or hasattr(request.user, "college_profile")
            or hasattr(request.user, "company_profile")
            or not hasattr(request.user, "trainer_profile")
        ):
            return HttpResponseForbidden("Trainer account access is required.")
        return view_func(request, *args, **kwargs)
    return wrapped


def home_view(request):
    """Root '/' — sends people to the dashboard that matches their role.
    The Admin Dashboard is the default landing page for the site's admin account,
    and the first dashboard shown if no role-specific profile is found."""
    if not request.user.is_authenticated:
        return redirect("login")
    user = request.user
    if hasattr(user, "admin_profile") or user.is_staff:
        return redirect("admin_dashboard")
    if hasattr(user, "college_profile"):
        return redirect("college_dashboard")
    if hasattr(user, "trainer_profile"):
        return redirect("trainer_dashboard")
    if hasattr(user, "company_profile"):
        return redirect("company_dashboard")
    if hasattr(user, "profile"):  # student
        return redirect("dashboard")
    return redirect("admin_dashboard")


@platform_admin_required
def admin_dashboard(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)

    partner_by_name = {college.name.casefold(): college for college in PartnerCollege.objects.all()}
    colleges = []
    for college in CollegeProfile.objects.select_related("user").filter(
        user__admin_profile__isnull=True, user__is_staff=False,
    ):
        partner = partner_by_name.get(college.college_name.casefold())
        colleges.append({
            "profile": college,
            "name": college.college_name,
            "students_count": (
                college.student_accounts.count() + college.students.count()
                + len(_unmatched_admin_student_records(college))
            ),
            "active_programs": college.programs.filter(status="active").count(),
            "pending_payment": partner.pending_payment if partner else 0,
            "status": partner.status if partner else "active",
        })
    total_students = sum(c["students_count"] for c in colleges)
    total_pending_payment = sum(float(summary.pending_payment) for summary in PartnerCollege.objects.all())

    tickets = SupportTicket.objects.all()
    open_tickets = tickets.exclude(status="Resolved")

    projects = AdminProject.objects.all()

    payment_buckets = {"Overdue (>30 Days)": 0, "Due (16-30 Days)": 0, "Due (1-15 Days)": 0, "Not Due": 0}
    # simple deterministic split of the outstanding total for the donut visual
    if total_pending_payment:
        payment_buckets["Overdue (>30 Days)"] = round(total_pending_payment * 0.39)
        payment_buckets["Due (16-30 Days)"] = round(total_pending_payment * 0.29)
        payment_buckets["Due (1-15 Days)"] = round(total_pending_payment * 0.17)
        payment_buckets["Not Due"] = round(total_pending_payment * 0.15)

    schedule_items = AdminScheduleItem.objects.all()
    assessment_schedule = schedule_items.filter(kind="assessment")[:5]
    interview_schedule = schedule_items.filter(kind="interview")[:5]

    today = timezone.localdate()
    trainer_rows = []
    for trainer in TrainerProfile.objects.select_related("user", "college").order_by("college__college_name", "user__first_name", "user__last_name", "user__username"):
        availability = trainer.availability.filter(date=today).order_by("date").first()
        trainer_rows.append({
            "trainer": trainer,
            "college_name": trainer.college.college_name if trainer.college else "Unassigned",
            "status": "Available" if availability is None or availability.is_available else "Not available",
            "note": availability.note if availability and availability.note else "Open for assignment",
            "assignments": trainer.assignments.all()[:3],
        })

    top_programs = TopProgram.objects.all()[:5]
    syllabus_updates = SyllabusUpdate.objects.all()[:5]

    context = {
        "profile": profile,
        "page_title": "Platform Operations Dashboard",
        "page_subtitle": "Transit Training and Recruitment Partner · Platform Administration",
        "user_role_label": "Super Admin",
        **_nav_context(ADMIN_NAV, "Platform Dashboard", "TRANSIT NEXUS", "LEARN · ASSESS · GROW"),
        "total_colleges": len(colleges),
        "total_students": total_students,
        "active_trainings": profile.active_trainings,
        "assessments_conducted": profile.assessments_conducted,
        "total_pending_payment": round(total_pending_payment),
        "open_issues": open_tickets.count(),
        "colleges": colleges[:8],
        "payment_buckets": payment_buckets,
        "tickets": tickets[:5],
        "projects": projects,
        "total_projects": projects.count(),
        "active_projects": projects.filter(status="In Progress").count(),
        "completed_projects": projects.filter(status="Completed").count(),
        "on_hold_projects": projects.filter(status="On Hold").count(),
        "assessment_schedule": assessment_schedule,
        "interview_schedule": interview_schedule,
        "trainer_roster": trainer_rows,
        "top_programs": top_programs,
        "syllabus_updates": syllabus_updates,
    }
    return render(request, "portal/admin_dashboard.html", context)


PREFERRED_DEPARTMENT_ORDER = [
    "Engineering",
    "Arts & Commerce",
    "Pharmacy",
    "Allied Health Science",
    "Architecture & Design",
    "Nursing",
    "Management",
]

DEPARTMENT_ALIASES = {
    "Engineering": {"Engineering", "ENG"},
    "Arts & Commerce": {"Arts & Commerce", "Arts and Commerce", "Commerce"},
    "Pharmacy": {"Pharmacy", "Pharmcy", "B.Pharm"},
    "Allied Health Science": {"Allied Health Science", "Allied Health Sciences"},
    "Architecture & Design": {"Architecture & Design", "Architecture and Design", "B.Arch", "Architecture"},
    "Nursing": {"Nursing", "B.Sc Nursing", "BSc Nursing"},
    "Management": {"Management", "MBA", "BBA"},
}


def _canonical_department_name(value):
    raw_name = (value or "").strip()
    if not raw_name:
        return ""
    lookup = raw_name.casefold()
    for canonical_name, aliases in DEPARTMENT_ALIASES.items():
        if lookup == canonical_name.casefold() or lookup in {alias.casefold() for alias in aliases}:
            return canonical_name
    return raw_name


def _department_sort_key(name):
    normalized = _canonical_department_name(name)
    try:
        return (0, PREFERRED_DEPARTMENT_ORDER.index(normalized))
    except ValueError:
        return (1, normalized.casefold())


def _semester_sort_key(label):
    normalized = (label or "").strip().casefold()
    if normalized.startswith("semester "):
        try:
            return (0, int(normalized.removeprefix("semester ").strip()))
        except ValueError:
            pass
    if normalized == "odd semester":
        return (1, 1)
    if normalized == "even semester":
        return (1, 2)
    return (2, normalized)


def _department_code_for_name(name):
    canonical = _canonical_department_name(name)
    aliases = DEPARTMENT_ALIASES.get(canonical, set())
    for alias in sorted(aliases, key=lambda value: (len(value), value)):
        if alias.isupper():
            return alias
    letters = "".join(ch for ch in canonical if ch.isalpha())[:4].upper()
    return letters or "GEN"


def _admin_student_records_by_name(profile):
    records_by_name = {}
    records = AdminStudentRecord.objects.filter(college_name__iexact=profile.college_name).order_by("pk")
    for record in records:
        record_key = record.name.strip().casefold()
        records_by_name.setdefault(record_key, []).append(record)
    return records_by_name


def _unmatched_admin_student_records(profile):
    records_by_name = _admin_student_records_by_name(profile)
    for student in profile.student_accounts.select_related("user"):
        student_name = (student.user.get_full_name() or student.user.username).strip().casefold()
        matching_records = records_by_name.get(student_name, [])
        if matching_records:
            matching_records.pop(0)
    return [record for records in records_by_name.values() for record in records]


def _department_summary_rows(profile):
    summary = {}
    admin_records_by_name = _admin_student_records_by_name(profile)

    for department in profile.departments.all():
        department_name = _canonical_department_name(department.name or department.code)
        if not department_name:
            continue
        summary[department_name] = {
            "pk": department.pk,
            "name": department_name,
            "code": department.code or _department_code_for_name(department_name),
            "total_students": department.total_students,
            "avg_performance": float(department.avg_performance or 0),
            "attendance_pct": float(department.attendance_pct or 0),
            "assessments_taken": department.assessments_taken,
            "training_hours": department.training_hours,
            "live_students": 0,
            "performance_values": [],
            "attendance_present": 0,
            "attendance_classes": 0,
            "live_training_hours": 0,
            "live_assessments": 0,
        }

    def get_entry(department_name):
        return summary.setdefault(department_name, {
            "name": department_name,
            "code": _department_code_for_name(department_name),
            "total_students": 0,
            "avg_performance": 0,
            "attendance_pct": 0,
            "assessments_taken": 0,
            "training_hours": 0,
            "live_students": 0,
            "performance_values": [],
            "attendance_present": 0,
            "attendance_classes": 0,
            "live_training_hours": 0,
            "live_assessments": 0,
        })

    for student in profile.student_accounts.all():
        student_name = (student.user.get_full_name() or student.user.username).strip().casefold()
        matching_records = admin_records_by_name.get(student_name, [])
        matching_record = matching_records.pop(0) if matching_records else None
        department_name = _canonical_department_name(
            student.department or (matching_record.department if matching_record else "")
        )
        if not department_name:
            continue
        entry = get_entry(department_name)
        entry["live_students"] += 1
        entry["live_training_hours"] += int(student.total_learning_hours or 0)
        enrollments = list(student.enrollments.all())
        if enrollments:
            entry["performance_values"].extend(float(enrollment.avg_score or 0) for enrollment in enrollments)
        elif matching_record:
            entry["performance_values"].append(float(matching_record.performance_pct or 0))
        for attendance in student.attendance_records.all():
            entry["attendance_present"] += attendance.present
            entry["attendance_classes"] += attendance.total_classes
        entry["live_assessments"] += student.assessments.count()

    for records in admin_records_by_name.values():
        for record in records:
            department_name = _canonical_department_name(record.department) or "Unassigned"
            entry = get_entry(department_name)
            entry["live_students"] += 1
            entry["performance_values"].append(float(record.performance_pct or 0))

    for student in profile.students.all():
        department_name = _canonical_department_name(student.department)
        if not department_name:
            continue
        entry = get_entry(department_name)
        entry["live_students"] += 1
        entry["performance_values"].append(float(student.avg_score or 0))
        entry["attendance_present"] += float(student.attendance_pct or 0)
        entry["attendance_classes"] += 100

    for assessment in profile.assessments.all():
        department_name = _canonical_department_name(assessment.department)
        if not department_name:
            continue
        get_entry(department_name)["live_assessments"] += 1

    rows = []
    has_live_students = any(values["live_students"] for values in summary.values())
    for values in summary.values():
        if has_live_students:
            values["total_students"] = values["live_students"]
        if values["performance_values"]:
            values["avg_performance"] = round(sum(values["performance_values"]) / len(values["performance_values"]), 1)
        if values["attendance_classes"]:
            values["attendance_pct"] = round(values["attendance_present"] / values["attendance_classes"] * 100, 1)
        if values["live_students"]:
            values["training_hours"] = values["live_training_hours"]
        if values["live_assessments"]:
            values["assessments_taken"] = values["live_assessments"]
        rows.append(Department(
            pk=values.get("pk"),
            name=values["name"],
            code=values["code"],
            total_students=values["total_students"],
            avg_performance=values["avg_performance"],
            attendance_pct=values["attendance_pct"],
            assessments_taken=values["assessments_taken"],
            training_hours=values["training_hours"],
        ))
    return sorted(rows, key=lambda department: _department_sort_key(department.name or department.code))


@college_account_required
def college_dashboard(request):
    profile = request.user.college_profile
    departments = _department_summary_rows(profile)

    tracked_students = (
        profile.student_accounts.count()
        + profile.students.count()
        + len(_unmatched_admin_student_records(profile))
    )
    total_students = tracked_students or sum(d.total_students for d in departments)
    if departments:
        avg_performance = round(sum(float(d.avg_performance) * d.total_students for d in departments) / total_students, 1) if total_students else 0
        avg_attendance = round(sum(float(d.attendance_pct) * d.total_students for d in departments) / total_students, 1) if total_students else 0
    else:
        avg_performance, avg_attendance = 0, 0

    total_assessments = profile.assessments.count() or sum(d.assessments_taken for d in departments)
    total_training_hours = sum(d.training_hours for d in departments)

    dist_buckets = {"Excellent (>=85%)": 0, "Good (70% - 84%)": 0, "Average (50% - 69%)": 0, "Needs Improvement (<50%)": 0}
    for d in departments:
        weight = d.total_students
        if d.avg_performance >= 85:
            dist_buckets["Excellent (>=85%)"] += weight
        elif d.avg_performance >= 70:
            dist_buckets["Good (70% - 84%)"] += weight
        elif d.avg_performance >= 50:
            dist_buckets["Average (50% - 69%)"] += weight
        else:
            dist_buckets["Needs Improvement (<50%)"] += weight

    dist_total = total_students or 1
    performance_distribution = [
        {"label": k, "count": v, "pct": round(v / dist_total * 100)} for k, v in dist_buckets.items()
    ]

    trend = profile.trend_points.all()
    trend_json = json.dumps({
        "labels": [t.month_label for t in trend],
        "values": [float(t.avg_percentage) for t in trend],
    })

    top_departments = sorted(departments, key=lambda d: _department_sort_key(d.name or d.code))[:3]
    quick_reports = profile.quick_reports.all()

    context = {
        "profile": profile,
        "page_title": f"{profile.college_name} — Dashboard",
        "page_subtitle": f"Academic Year: {profile.academic_year}",
        "user_role_label": "College Admin",
        **_nav_context(COLLEGE_NAV, "Dashboard", "TRANSIT NEXUS", "LEARN · ASSESS · GROW"),
        "departments": departments,
        "total_students": total_students,
        "avg_performance": avg_performance,
        "avg_attendance": avg_attendance,
        "total_assessments": total_assessments,
        "total_training_hours": total_training_hours,
        "placement_eligible": profile.placement_eligible,
        "performance_distribution": performance_distribution,
        "trend_json": trend_json,
        "top_departments": top_departments,
        "quick_reports": quick_reports,
    }
    return render(request, "portal/college_dashboard.html", context)


@login_required
def trainer_dashboard(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    batches = profile.batches.all()
    total_students = sum(b.total_students for b in batches)
    total_present = sum(b.present_count for b in batches)
    total_absent = sum(b.absent_count for b in batches)
    overall_attendance = round((total_present / (total_present + total_absent)) * 100) if (total_present + total_absent) else 0

    assessments = profile.assessments.all()[:5]
    pending_tasks = profile.pending_tasks.all()
    trend = profile.trend_points.all()
    trend_json = json.dumps({
        "labels": [t.month_label for t in trend],
        "values": [float(t.avg_percentage) for t in trend],
    })

    context = {
        "profile": profile,
        "page_title": f"Good Morning, {profile.user.first_name}!",
        "page_subtitle": "Here's what's happening with your batches",
        "user_role_label": "Trainer",
        **_nav_context(TRAINER_NAV, "Dashboard", "TRANSIT NEXUS", "LEARN · ASSESS · GROW"),
        "batches": batches,
        "total_batches": batches.count(),
        "total_students": total_students,
        "overall_attendance": overall_attendance,
        "total_present": total_present,
        "total_absent": total_absent,
        "assessments": assessments,
        "pending_tasks": pending_tasks,
        "trend_json": trend_json,
    }
    return render(request, "portal/trainer_dashboard.html", context)


@login_required
def company_dashboard(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    candidates = profile.candidates.all()
    interviews = profile.interviews.all()

    stage_counts = {
        "Scheduled": interviews.filter(status="scheduled").count(),
        "In Progress": interviews.filter(status="in_progress").count(),
        "Completed": interviews.filter(status="completed").count(),
        "Cancelled": interviews.filter(status="cancelled").count(),
    }
    total_interviews = interviews.count()

    top_candidates = sorted(candidates, key=lambda c: -c.overall_score)[:5]

    context = {
        "profile": profile,
        "page_title": f"Welcome, {profile.company_name}",
        "page_subtitle": "Track your hiring pipeline",
        "user_role_label": "Company / HR",
        **_nav_context(COMPANY_NAV, "Dashboard", "TRANSIT NEXUS", "LEARN · ASSESS · GROW"),
        "total_drives": profile.total_drives,
        "shortlisted": candidates.count(),
        "total_interviews": total_interviews,
        "hired": profile.hired,
        "candidates": candidates,
        "top_candidates": top_candidates,
        "upcoming_interviews": interviews.filter(status="scheduled")[:5],
        "stage_counts": stage_counts,
    }
    return render(request, "portal/company_dashboard.html", context)


# =========================================================
# ADMIN — sub-pages
# =========================================================

@platform_admin_required
def admin_colleges(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    partner_by_name = {college.name.casefold(): college for college in PartnerCollege.objects.all()}
    colleges = []
    profiles = CollegeProfile.objects.select_related("user").filter(
        user__admin_profile__isnull=True, user__is_staff=False,
    )
    for college in profiles:
        partner = partner_by_name.get(college.college_name.casefold())
        colleges.append({
            "profile": college,
            "name": college.college_name,
            "location": college.location,
            "students_count": (
                college.student_accounts.count() + college.students.count()
                + len(_unmatched_admin_student_records(college))
            ),
            "active_programs": college.programs.filter(status="active").count(),
            "pending_payment": partner.pending_payment if partner else 0,
            "status": partner.status if partner else "active",
        })
    ctx = _page_ctx(profile, ADMIN_NAV, "Colleges", "Colleges",
                    f"{len(colleges)} college workspaces", "Platform Admin",
                    colleges=colleges)
    return render(request, "portal/admin_colleges.html", ctx)


@platform_admin_required
def admin_college_detail(request, college_id):
    admin_profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    college = get_object_or_404(
        CollegeProfile.objects.select_related("user").filter(
            user__admin_profile__isnull=True, user__is_staff=False,
        ),
        pk=college_id,
    )
    entry_forms = {
        "add_student": (CollegeStudentForm, "students", "Student"),
        "add_program": (CollegeProgramForm, "programs", "Training program"),
        "add_assessment": (CollegeAssessmentForm, "assessments", "Assessment"),
        "add_department": (DepartmentAttendanceForm, "attendance", "Department attendance"),
        "add_payment": (CollegeInvoiceForm, "payments", "Invoice"),
        "add_placement": (PlacementRecordForm, "placements", "Placement"),
        "add_syllabus": (SyllabusCoverageForm, "syllabus", "Syllabus coverage"),
        "add_report": (CollegeQuickReportForm, "reports", "Report"),
    }
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "toggle_attendance":
            department = college.departments.filter(pk=request.POST.get("department_id", "")).first()
            enabled_value = request.POST.get("enabled", "")
            if department is None or enabled_value not in {"0", "1"}:
                messages.error(request, "Choose a valid department attendance setting.")
            else:
                department.attendance_enabled = enabled_value == "1"
                department.save(update_fields=["attendance_enabled"])
                messages.success(request, f"Attendance tracking {'enabled' if department.attendance_enabled else 'disabled'} for {department.name}.")
            return redirect(f"{reverse('admin_college_detail', args=[college.pk])}#attendance")
        if action in entry_forms:
            form_class, section, record_label = entry_forms[action]
            form = form_class(request.POST)
            if form.is_valid():
                record = form.save(commit=False)
                if isinstance(record, AdminInvoice):
                    record.college_name = college.college_name
                else:
                    record.college = college
                record.save()
                messages.success(request, f"{record_label} saved for {college.college_name}.")
            else:
                for field_name, errors in form.errors.items():
                    field_label = form.fields[field_name].label or field_name
                    for error in errors:
                        messages.error(request, f"{field_label}: {error}")
            return redirect(f"{reverse('admin_college_detail', args=[college.pk])}#{section}")

    partner = PartnerCollege.objects.filter(name__iexact=college.college_name).first()
    manual_students = college.students.all()
    student_accounts = college.student_accounts.select_related("user").prefetch_related("enrollments", "attendance_records")
    imported_student_records = _admin_student_records_by_name(college)
    students = []
    for student in manual_students:
        students.append({
            "name": student.name,
            "department": _canonical_department_name(student.department) or "Unassigned",
            "semester": college.semester_label or "Unassigned",
            "avg_score": student.avg_score,
            "attendance_pct": student.attendance_pct,
            "is_account": False,
        })
    for account in student_accounts:
        display_name = account.user.get_full_name() or account.user.username
        matching_records = imported_student_records.get(display_name.strip().casefold(), [])
        imported_record = matching_records.pop(0) if matching_records else None
        enrollments = list(account.enrollments.all())
        attendance_rows = list(account.attendance_records.all())
        semester = account.semester_label
        if not semester or semester == "Current Semester":
            semester = college.semester_label
        students.append({
            "name": display_name,
            "department": _canonical_department_name(
                account.department or (imported_record.department if imported_record else "")
            ) or "Unassigned",
            "semester": semester or "Unassigned",
            "avg_score": (
                round(sum(float(item.avg_score or 0) for item in enrollments) / len(enrollments), 1)
                if enrollments else (imported_record.performance_pct if imported_record else None)
            ),
            "attendance_pct": (
                round(sum(item.percentage for item in attendance_rows) / len(attendance_rows), 1)
                if attendance_rows else None
            ),
            "is_account": True,
        })
    for records in imported_student_records.values():
        for record in records:
            students.append({
                "name": record.name,
                "department": _canonical_department_name(record.department) or "Unassigned",
                "semester": college.semester_label or "Unassigned",
                "avg_score": record.performance_pct,
                "attendance_pct": None,
                "is_account": False,
            })
    students.sort(key=lambda row: (
        _department_sort_key(row["department"]),
        _semester_sort_key(row["semester"]),
        row["name"].casefold(),
    ))
    student_groups = []
    for student in students:
        group_key = (student["department"], student["semester"])
        if not student_groups or student_groups[-1]["key"] != group_key:
            student_groups.append({
                "key": group_key,
                "department": student["department"],
                "semester": student["semester"],
                "students": [],
            })
        student_groups[-1]["students"].append(student)
    programs = college.programs.all()
    assessments = college.assessments.all()
    departments = college.departments.all()
    placements = college.placements.all()
    faculty = college.faculty.all()
    syllabus_coverage = college.syllabus_coverage.all()
    invoices = AdminInvoice.objects.filter(college_name__iexact=college.college_name)
    reports = college.quick_reports.all()
    total_pending = partner.pending_payment if partner else sum(
        invoice.amount for invoice in invoices if invoice.status in {"due", "overdue"}
    )
    ctx = _page_ctx(
        admin_profile, ADMIN_NAV, "Colleges", college.college_name,
        f"{college.location} · College workspace", "Platform Admin",
        college=college, students=students, student_groups=student_groups,
        programs=programs, assessments=assessments,
        departments=departments, placements=placements, faculty=faculty,
        syllabus_coverage=syllabus_coverage, invoices=invoices, reports=reports,
        student_form=CollegeStudentForm(), program_form=CollegeProgramForm(),
        assessment_form=CollegeAssessmentForm(), attendance_form=DepartmentAttendanceForm(),
        payment_form=CollegeInvoiceForm(), placement_form=PlacementRecordForm(),
        syllabus_form=SyllabusCoverageForm(), report_form=CollegeQuickReportForm(),
        total_students=len(students), total_programs=programs.count(),
        total_assessments=assessments.count(), total_faculty=faculty.count(),
        total_placed=sum(item.students_placed for item in placements),
        total_pending_payment=total_pending,
    )
    return render(request, "portal/admin_college_detail.html", ctx)


@platform_admin_required
def admin_trainers(request):
    admin_profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        domain = request.POST.get("domain", "").strip()
        college_id = request.POST.get("college", "").strip()
        if not username or not password or not first_name or not email or not domain:
            messages.error(request, "Username, password, name, email, and domain are required.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already in use.")
        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, f"Email '{email}' is already in use.")
        elif college_id and not CollegeProfile.objects.filter(pk=college_id).exists():
            messages.error(request, "Choose a valid college.")
        else:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username, password=password, email=email,
                    first_name=first_name, last_name=last_name, is_active=False,
                )
                college = CollegeProfile.objects.filter(pk=college_id).first() if college_id else None
                TrainerProfile.objects.create(user=user, college=college, domain=domain, phone=phone)
            messages.success(request, f"Trainer '{user.get_full_name() or user.username}' was created. Approve the account in Users & Roles to allow sign in.")
            return redirect("admin_trainers")

    trainers = TrainerProfile.objects.select_related("user", "college").order_by(
        "user__first_name", "user__last_name", "user__username"
    )
    ctx = _page_ctx(
        admin_profile, ADMIN_NAV, "Trainers", "Trainer Directory",
        f"{trainers.count()} trainers", "Platform Admin",
        trainers=trainers, colleges=CollegeProfile.objects.order_by("college_name"),
    )
    return render(request, "portal/admin_trainers.html", ctx)


@platform_admin_required
def admin_students(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    student_rows = []
    colleges = CollegeProfile.objects.order_by("college_name")
    for college in colleges:
        records_by_name = _admin_student_records_by_name(college)
        for student in college.student_accounts.select_related("user").prefetch_related("enrollments", "attendance_records"):
            name = student.user.get_full_name() or student.user.username
            matching_records = records_by_name.get(name.strip().casefold(), [])
            matching_record = matching_records.pop(0) if matching_records else None
            enrollments = list(student.enrollments.all())
            attendance_rows = list(student.attendance_records.all())
            semester = student.semester_label
            if not semester or semester == "Current Semester":
                semester = college.semester_label
            student_rows.append({
                "name": name,
                "college_name": college.college_name,
                "academic_year": college.academic_year,
                "department": _canonical_department_name(
                    student.department or (matching_record.department if matching_record else "")
                ) or "Unassigned",
                "semester": semester or "Unassigned",
                "performance_pct": (
                    round(sum(float(e.avg_score or 0) for e in enrollments) / len(enrollments), 1)
                    if enrollments else (matching_record.performance_pct if matching_record else None)
                ),
                "attendance_pct": (
                    round(sum(row.percentage for row in attendance_rows) / len(attendance_rows), 1)
                    if attendance_rows else None
                ),
                "status": "Active" if student.user.is_active else "Pending",
                "has_account": True,
            })
        for records in records_by_name.values():
            for record in records:
                student_rows.append({
                    "name": record.name,
                    "college_name": college.college_name,
                    "academic_year": college.academic_year,
                    "department": _canonical_department_name(record.department) or "Unassigned",
                    "semester": college.semester_label or "Unassigned",
                    "performance_pct": record.performance_pct,
                    "attendance_pct": None,
                    "status": record.status,
                    "has_account": False,
                })
        for student in college.students.all():
            student_rows.append({
                "name": student.name,
                "college_name": college.college_name,
                "academic_year": college.academic_year,
                "department": _canonical_department_name(student.department) or "Unassigned",
                "semester": college.semester_label or "Unassigned",
                "performance_pct": student.avg_score,
                "attendance_pct": student.attendance_pct,
                "status": "Active",
                "has_account": False,
            })
    student_rows.sort(key=lambda row: (
        row["college_name"].casefold(), _department_sort_key(row["department"]),
        _semester_sort_key(row["semester"]), row["name"].casefold(),
    ))
    student_groups = []
    for row in student_rows:
        key = (row["college_name"], row["department"], row["semester"])
        if not student_groups or student_groups[-1]["key"] != key:
            student_groups.append({
                "key": key,
                "college_name": row["college_name"],
                "academic_year": row["academic_year"],
                "department": row["department"],
                "semester": row["semester"],
                "students": [],
            })
        student_groups[-1]["students"].append(row)
    ctx = _page_ctx(profile, ADMIN_NAV, "Students Management", "Students Management",
                    f"{len(student_rows)} students across the platform", "Super Admin",
                    students=student_rows, student_groups=student_groups)
    return render(request, "portal/admin_students.html", ctx)


@platform_admin_required
def admin_programs(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    programs = TopProgram.objects.all()
    ctx = _page_ctx(profile, ADMIN_NAV, "Training Programs", "Training Programs",
                    f"{programs.count()} programs running", "Super Admin", programs=programs)
    return render(request, "portal/admin_programs.html", ctx)


@platform_admin_required
def admin_assessments(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    items = AdminScheduleItem.objects.filter(kind="assessment")
    ctx = _page_ctx(profile, ADMIN_NAV, "Assessments", "Assessments",
                    f"{items.count()} assessments scheduled platform-wide", "Super Admin", items=items)
    return render(request, "portal/admin_assessments.html", ctx)


@platform_admin_required
def admin_interviews(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    items = AdminScheduleItem.objects.filter(kind="interview")
    ctx = _page_ctx(profile, ADMIN_NAV, "Interviews", "Interviews",
                    f"{items.count()} interview drives scheduled", "Super Admin", items=items)
    return render(request, "portal/admin_interviews.html", ctx)


@platform_admin_required
def admin_projects(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    projects = AdminProject.objects.all()
    ctx = _page_ctx(profile, ADMIN_NAV, "Projects", "Projects",
                    f"{projects.count()} projects across all colleges", "Super Admin", projects=projects)
    return render(request, "portal/admin_projects.html", ctx)


@platform_admin_required
def admin_syllabus(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    updates = SyllabusUpdate.objects.all()
    ctx = _page_ctx(profile, ADMIN_NAV, "Syllabus Management", "Syllabus Management",
                    f"{updates.count()} recent updates", "Super Admin", updates=updates)
    return render(request, "portal/admin_syllabus.html", ctx)


@platform_admin_required
def admin_schedules(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    items = AdminScheduleItem.objects.all()
    ctx = _page_ctx(profile, ADMIN_NAV, "Schedules", "Schedules",
                    "All assessments & interviews across the platform", "Super Admin", items=items)
    return render(request, "portal/admin_schedules.html", ctx)


@platform_admin_required
def admin_attendance(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    summaries = AdminAttendanceSummary.objects.all()
    avg_pct = round(sum(float(s.attendance_pct) for s in summaries) / len(summaries), 1) if summaries else 0
    ctx = _page_ctx(profile, ADMIN_NAV, "Attendance", "Attendance",
                    "Attendance summary across all colleges", "Super Admin",
                    summaries=summaries, avg_pct=avg_pct)
    return render(request, "portal/admin_attendance.html", ctx)


@platform_admin_required
def admin_payments(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    invoices = AdminInvoice.objects.all()
    total_paid = sum(float(i.amount) for i in invoices if i.status == "paid")
    total_due = sum(float(i.amount) for i in invoices if i.status in ("due", "overdue"))
    ctx = _page_ctx(profile, ADMIN_NAV, "Payments & Invoices", "Payments & Invoices",
                    "Track invoices across every partner college", "Super Admin",
                    invoices=invoices, total_paid=round(total_paid), total_due=round(total_due))
    return render(request, "portal/admin_payments.html", ctx)


@platform_admin_required
def admin_reports(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    ctx = _page_ctx(profile, ADMIN_NAV, "Reports & Analytics", "Reports & Analytics",
                    "Platform-wide reports", "Super Admin")
    return render(request, "portal/admin_reports.html", ctx)


@platform_admin_required
def admin_support(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    tickets = SupportTicket.objects.all()
    ctx = _page_ctx(profile, ADMIN_NAV, "Support & Issues", "Support & Issues",
                    f"{tickets.exclude(status='Resolved').count()} open tickets", "Super Admin", tickets=tickets)
    return render(request, "portal/admin_support.html", ctx)


@platform_admin_required
def admin_users(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    if request.method == "POST" and request.user.is_staff:
        if request.POST.get("action") == "approve_pending":
            pending_users = User.objects.filter(is_active=False).exclude(pk=request.user.pk)
            approved_count = pending_users.update(is_active=True)
            messages.success(request, f"Approved {approved_count} pending account(s).")
            return redirect("admin_users")
        if request.POST.get("action") == "create":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "")
            role = request.POST.get("role", "student")
            college_name = request.POST.get("college_name", "").strip()
            if not username or not password:
                messages.error(request, "Username and password are required.")
            elif role == "college" and not college_name:
                messages.error(request, "College name is required for a College account.")
            elif role == "college" and CollegeProfile.objects.filter(college_name__iexact=college_name).exists():
                messages.error(request, "A college account with that college name already exists.")
            elif role in {"student", "trainer"} and not college_name:
                messages.error(request, "College name is required for a Student or Trainer account.")
            elif role == "student" and not request.POST.get("department", "").strip():
                messages.error(request, "Department is required for a Student account.")
            elif role == "student" and not CollegeProfile.objects.filter(college_name__iexact=college_name).exists():
                messages.error(request, "Create the college account before creating its student accounts.")
            elif role == "student":
                department = request.POST.get("department", "").strip()
                canonical_department = _canonical_department_name(department)
                allowed_departments = set(PREFERRED_DEPARTMENT_ORDER)
                if canonical_department not in allowed_departments:
                    messages.error(request, "Choose a valid department for the student account.")
                    return redirect("admin_users")
            elif role == "trainer" and not CollegeProfile.objects.filter(college_name__iexact=college_name).exists():
                messages.error(request, "Create the college account before creating its trainer accounts.")
            elif User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' already exists.")
            else:
                student_college = CollegeProfile.objects.filter(college_name__iexact=college_name).first() if role == "student" else None
                trainer_college = CollegeProfile.objects.filter(college_name__iexact=college_name).first() if role == "trainer" else None
                student_department = canonical_department if role == "student" else ""
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=request.POST.get("first_name", "").strip(),
                    last_name=request.POST.get("last_name", "").strip(),
                    email=request.POST.get("email", "").strip(),
                    is_active=False,
                )
                if role == "owner":
                    user.is_staff = True
                    user.is_superuser = True
                    user.save(update_fields=["is_staff", "is_superuser"])
                    AdminProfile.objects.create(user=user)
                elif role == "college":
                    college_location = request.POST.get("college_location", "").strip()
                    CollegeProfile.objects.create(
                        user=user,
                        college_name=college_name,
                        location=college_location or "Not specified",
                    )
                    PartnerCollege.objects.get_or_create(name=college_name)
                elif role == "trainer":
                    TrainerProfile.objects.create(user=user, college=trainer_college)
                elif role == "company":
                    CompanyProfile.objects.create(user=user, company_name=user.get_full_name() or username)
                elif role == "student":
                    StudentProfile.objects.create(user=user, college=student_college, department=student_department)
                    AdminStudentRecord.objects.create(
                        name=user.get_full_name() or user.username,
                        college_name=college_name,
                        department=student_department,
                        status="Pending",
                    )
                messages.success(request, f"{role.title()} account created as Pending.")
            return redirect("admin_users")

        user_id = request.POST.get("user_id")
        target = User.objects.filter(pk=user_id).first()
        if target is None:
            messages.error(request, "That account no longer exists.")
        elif target == request.user:
            messages.error(request, "You cannot change or delete your own administrator account.")
        elif request.POST.get("action") == "delete":
            username = target.username
            target.delete()
            messages.success(request, f"Account '{username}' deleted.")
        else:
            target.is_active = request.POST.get("action") == "approve"
            target.save(update_fields=["is_active"])
            status = "approved" if target.is_active else "disabled"
            messages.success(request, f"Account '{target.username}' {status}.")
        return redirect("admin_users")

    selected_college = request.GET.get("college_filter", "").strip()
    selected_role_tab = request.GET.get("role_tab", "all").strip().lower()
    college_options = list(CollegeProfile.objects.order_by("college_name").values_list("college_name", flat=True).distinct())
    department_options = PREFERRED_DEPARTMENT_ORDER
    users = User.objects.all().order_by("username")
    rows = []
    for u in users:
        if hasattr(u, "admin_profile"):
            role = "Super Admin"
            normalized_role = "admin"
        elif hasattr(u, "college_profile"):
            role = "College Admin"
            normalized_role = "college"
        elif hasattr(u, "trainer_profile"):
            role = "Trainer"
            normalized_role = "trainer"
        elif hasattr(u, "company_profile"):
            role = "Company / HR"
            normalized_role = "company"
        elif hasattr(u, "profile"):
            role = "Student"
            normalized_role = "student"
        else:
            role = "Unassigned"
            normalized_role = "all"

        if selected_role_tab != "all" and normalized_role != selected_role_tab:
            continue

        if selected_college:
            if role != "Student":
                continue
            student_profile = getattr(u, "profile", None)
            if not student_profile or not student_profile.college or student_profile.college.college_name != selected_college:
                continue

        rows.append({"user": u, "role": role})

    total_accounts = len(rows)
    student_accounts = sum(1 for row in rows if row["role"] == "Student")
    college_accounts = sum(1 for row in rows if row["role"] == "College Admin")
    pending_accounts = sum(1 for row in rows if not row["user"].is_active)

    ctx = _page_ctx(profile, ADMIN_NAV, "Users & Roles", "Users & Roles",
                    f"{total_accounts} total accounts", "Super Admin",
                    rows=rows, college_options=college_options, department_options=department_options,
                    selected_college=selected_college, selected_role_tab=selected_role_tab,
                    total_accounts=total_accounts, student_accounts=student_accounts,
                    college_accounts=college_accounts, pending_accounts=pending_accounts)
    return render(request, "portal/admin_users.html", ctx)


@platform_admin_required
def bulk_import(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    templates = {
        "students": ["username", "password", "first_name", "last_name", "email", "college_name", "department"],
        "colleges": ["username", "password", "first_name", "last_name", "email", "college_name", "location"],
        "trainers": ["username", "password", "first_name", "last_name", "email"],
        "companies": ["username", "password", "first_name", "last_name", "email", "company_name"],
    }
    ctx = _page_ctx(profile, ADMIN_NAV, "Bulk Import", "Bulk Import",
                    "Import accounts and profile records from CSV files", "Super Admin")

    requested_template = request.GET.get("template")
    if requested_template in templates:
        response = HttpResponse(",".join(templates[requested_template]) + "\n", content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{requested_template}_template.csv"'
        return response

    errors = []
    if request.method == "POST":
        role = request.POST.get("role", "").strip().lower()
        uploaded = request.FILES.get("file")
        if role not in templates:
            errors.append("Choose a valid account type.")
        elif not uploaded:
            errors.append("Choose a CSV file to import.")
        elif uploaded.size > 5 * 1024 * 1024:
            errors.append("The CSV file must be 5 MB or smaller.")
        else:
            try:
                content = uploaded.read().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(content))
                headers = [header.strip().lower() for header in (reader.fieldnames or [])]
                required = {"username", "password"}
                if role in {"students", "colleges"}:
                    required.add("college_name")
                if role == "students":
                    required.add("department")
                if role == "companies":
                    required.add("company_name")
                missing = sorted(required - set(headers))
                if missing:
                    errors.append("Missing required columns: " + ", ".join(missing))
                else:
                    rows = []
                    seen_usernames = set()
                    for row_number, raw_row in enumerate(reader, start=2):
                        row = {
                            (key or "").strip().lower(): (value or "").strip()
                            for key, value in raw_row.items()
                            if key is not None
                        }
                        if not any(row.values()):
                            continue
                        username = row.get("username", "")
                        if not username:
                            errors.append(f"Row {row_number}: username is required.")
                        elif username in seen_usernames:
                            errors.append(f"Row {row_number}: duplicate username '{username}' in this file.")
                        elif User.objects.filter(username=username).exists():
                            errors.append(f"Row {row_number}: username '{username}' already exists.")
                        else:
                            seen_usernames.add(username)
                        if not row.get("password"):
                            errors.append(f"Row {row_number}: password is required.")
                        for field in required - {"username", "password"}:
                            if not row.get(field):
                                errors.append(f"Row {row_number}: {field} is required.")
                        if role == "students" and row.get("college_name") and not CollegeProfile.objects.filter(
                            college_name__iexact=row["college_name"],
                        ).exists():
                            errors.append(f"Row {row_number}: college '{row['college_name']}' has no college account.")
                        rows.append((row_number, row))

                    if len(rows) > 10000:
                        errors.append("A single import can contain at most 10,000 records.")
                    if not rows:
                        errors.append("The CSV file contains no data rows.")
                    if errors:
                        errors = errors[:30]
                    else:
                        import_succeeded = False
                        for attempt in range(3):
                            try:
                                with transaction.atomic():
                                    for _, row in rows:
                                        user = User.objects.create_user(
                                            username=row["username"],
                                            password=row["password"],
                                            first_name=row.get("first_name", ""),
                                            last_name=row.get("last_name", ""),
                                            email=row.get("email", ""),
                                            is_active=False,
                                        )
                                        if role == "students":
                                            student_college = CollegeProfile.objects.get(college_name__iexact=row["college_name"])
                                            StudentProfile.objects.create(
                                                user=user, college=student_college, department=row["department"],
                                            )
                                            AdminStudentRecord.objects.create(
                                                name=user.get_full_name() or user.username,
                                                college_name=row["college_name"],
                                                department=row["department"],
                                                status="Pending",
                                            )
                                        elif role == "colleges":
                                            college_name = row["college_name"]
                                            CollegeProfile.objects.create(
                                                user=user,
                                                college_name=college_name,
                                                location=row.get("location", ""),
                                            )
                                            PartnerCollege.objects.get_or_create(name=college_name)
                                        elif role == "trainers":
                                            TrainerProfile.objects.create(user=user)
                                        else:
                                            CompanyProfile.objects.create(
                                                user=user,
                                                company_name=row["company_name"],
                                            )
                                import_succeeded = True
                                break
                            except OperationalError as exc:
                                if "locked" not in str(exc).casefold() or attempt == 2:
                                    break
                                connections["default"].close()
                                time.sleep(0.5 * (attempt + 1))

                        if import_succeeded:
                            messages.success(request, f"Imported {len(rows)} pending {role} account(s). Review and approve them in Users & Roles.")
                            return redirect("bulk_import")
                        errors.append("The database is busy. Stop any other Django server, shell, or import process and try again.")
            except (UnicodeDecodeError, csv.Error):
                errors.append("Could not read that file as a valid UTF-8 CSV. Download a template and try again.")

    ctx["errors"] = errors
    ctx["template_roles"] = templates.keys()
    return render(request, "portal/bulk_import.html", ctx)


@platform_admin_required
def admin_communications(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    announcements = Announcement.objects.all()
    ctx = _page_ctx(profile, ADMIN_NAV, "Communications", "Communications",
                    "Announcements sent to colleges", "Super Admin", announcements=announcements)
    return render(request, "portal/admin_communications.html", ctx)


@platform_admin_required
def admin_settings(request):
    profile, _ = AdminProfile.objects.get_or_create(user=request.user)
    user = profile.user
    if request.method == "POST":
        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.last_name = request.POST.get("last_name", user.last_name).strip()
        user.email = request.POST.get("email", user.email).strip()
        user.save()
        messages.success(request, "Settings updated successfully.")
        return redirect("admin_settings")
    ctx = _page_ctx(profile, ADMIN_NAV, "Settings", "Settings", "Manage your admin account", "Super Admin")
    return render(request, "portal/admin_settings.html", ctx)


# =========================================================
# COLLEGE — sub-pages
# =========================================================

def _college_record_context(request, profile, model, form_class, page_name):
    records = model.objects.filter(college=profile)
    record_id = request.POST.get("record_id", "").strip() if request.method == "POST" else request.GET.get("edit", "")
    if record_id and not record_id.isdecimal():
        if request.method == "POST":
            messages.error(request, "That record was not found for your college.")
        return redirect(page_name)
    instance = records.filter(pk=record_id).first() if record_id else None

    if request.method == "POST":
        if request.POST.get("action") == "delete":
            if instance is None:
                messages.error(request, "That record was not found for your college.")
            else:
                instance.delete()
                messages.success(request, "Record deleted.")
            return redirect(page_name)
        if record_id and instance is None:
            messages.error(request, "That record was not found for your college.")
            return redirect(page_name)

        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            record = form.save(commit=False)
            record.college = profile
            record.save()
            messages.success(request, "Record updated." if instance else "Record created.")
            return redirect(page_name)
    else:
        form = form_class(instance=instance)

    return {
        "records": records,
        "edit_record": instance,
        "record_form": form,
    }


COLLEGE_CSV_IMPORTS = {
    "students": {
        "filename": "students_template.csv",
        "headers": ["name", "department", "avg_score", "attendance_pct"],
        "required": {"name", "department"},
        "form": CollegeStudentForm,
        "model": CollegeStudent,
    },
    "programs": {
        "filename": "programs_template.csv",
        "headers": ["name", "students_count", "status"],
        "required": {"name"},
        "form": CollegeProgramForm,
        "model": CollegeProgram,
    },
    "assessments": {
        "filename": "assessments_template.csv",
        "headers": ["name", "department", "date", "avg_score", "status"],
        "required": {"name", "department", "date"},
        "form": CollegeAssessmentForm,
        "model": CollegeAssessment,
    },
    "attendance": {
        "filename": "attendance_template.csv",
        "headers": ["code", "name", "total_students", "attendance_pct", "avg_performance", "assessments_taken", "training_hours"],
        "required": {"code", "name", "attendance_pct"},
        "form": DepartmentAttendanceForm,
        "model": Department,
        "upsert": "code",
    },
    "payments": {
        "filename": "payments_template.csv",
        "headers": ["invoice_no", "amount", "issued_date", "status"],
        "required": {"invoice_no", "amount", "issued_date"},
        "form": CollegeInvoiceForm,
        "model": AdminInvoice,
        "upsert": "invoice_no",
    },
    "placements": {
        "filename": "placements_template.csv",
        "headers": ["company_name", "students_placed", "package_lpa", "drive_date"],
        "required": {"company_name", "drive_date"},
        "form": PlacementRecordForm,
        "model": PlacementRecord,
    },
    "syllabus": {
        "filename": "syllabus_template.csv",
        "headers": ["subject", "department", "coverage_pct"],
        "required": {"subject", "department", "coverage_pct"},
        "form": SyllabusCoverageForm,
        "model": SyllabusCoverage,
    },
    "faculty": {
        "filename": "faculty_template.csv",
        "headers": ["name", "department", "rating", "classes_taken"],
        "required": {"name", "department"},
        "form": FacultyForm,
        "model": Faculty,
    },
    "reports": {
        "filename": "reports_template.csv",
        "headers": ["title"],
        "required": {"title"},
        "form": CollegeQuickReportForm,
        "model": CollegeQuickReport,
    },
}

COLLEGE_UPLOAD_PAGE = {
    "students": "college_students",
    "programs": "college_programs",
    "assessments": "college_assessments",
    "attendance": "college_attendance",
    "payments": "college_payments",
    "placements": "college_placements",
    "syllabus": "college_syllabus",
    "faculty": "college_faculty",
    "reports": "college_reports",
}


@college_account_required
def college_csv_upload(request, dataset):
    config = COLLEGE_CSV_IMPORTS.get(dataset)
    if config is None:
        raise Http404("Unknown college data type.")
    if request.method == "GET" and request.GET.get("template") == "1":
        output = io.StringIO(newline="")
        csv.writer(output).writerow(config["headers"])
        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{config["filename"]}"'
        return response
    if request.method != "POST":
        return HttpResponseForbidden("Upload a CSV file using the college page form.")

    uploaded = request.FILES.get("file")
    if not uploaded:
        messages.error(request, "Choose a CSV file to upload.")
        return redirect(COLLEGE_UPLOAD_PAGE[dataset])
    if uploaded.size > 5 * 1024 * 1024:
        messages.error(request, "CSV files must be 5 MB or smaller.")
        return redirect(COLLEGE_UPLOAD_PAGE[dataset])

    try:
        reader = csv.DictReader(io.StringIO(uploaded.read().decode("utf-8-sig")))
        raw_headers = reader.fieldnames or []
        headers = [(header or "").strip().lower() for header in raw_headers]
        if not headers or any(not header for header in headers) or len(headers) != len(set(headers)):
            raise ValueError("CSV must have one unique, non-empty header for each column.")
        missing = sorted(config["required"] - set(headers))
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))

        prepared = []
        errors = []
        seen_keys = set()
        for row_number, raw_row in enumerate(reader, start=2):
            row = {
                (key or "").strip().lower(): (value or "").strip()
                for key, value in raw_row.items()
                if key is not None
            }
            if not any(row.values()):
                continue
            for required in config["required"]:
                if not row.get(required):
                    errors.append(f"Row {row_number}: {required} is required.")

            instance = None
            upsert_field = config.get("upsert")
            identity = row.get(upsert_field, "") if upsert_field else ""
            if upsert_field and identity:
                if identity in seen_keys:
                    errors.append(f"Row {row_number}: duplicate {upsert_field} '{identity}' in this file.")
                seen_keys.add(identity)
                if dataset == "attendance":
                    instance = request.user.college_profile.departments.filter(code=identity).first()
                else:
                    instance = AdminInvoice.objects.filter(
                        college_name__iexact=request.user.college_profile.college_name,
                        invoice_no=identity,
                    ).first()

            form_data = {key: value for key, value in row.items() if value != ""}
            form = config["form"](form_data, instance=instance)
            if not form.is_valid():
                for field, field_errors in form.errors.items():
                    errors.extend(f"Row {row_number}: {field}: {error}" for error in field_errors)
            prepared.append((form, instance))

        if len(prepared) > 10000:
            errors.append("A single upload can contain at most 10,000 rows.")
        if not prepared:
            errors.append("The CSV file contains no data rows.")
        if errors:
            for error in errors[:30]:
                messages.error(request, error)
            return redirect(COLLEGE_UPLOAD_PAGE[dataset])

        profile = request.user.college_profile
        with transaction.atomic():
            for form, _ in prepared:
                record = form.save(commit=False)
                if isinstance(record, AdminInvoice):
                    record.college_name = profile.college_name
                else:
                    record.college = profile
                record.save()
        messages.success(request, f"Uploaded {len(prepared)} {dataset} row(s) for {profile.college_name}.")
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        messages.error(request, str(error) or "Could not read that file as a valid UTF-8 CSV.")

    return redirect(COLLEGE_UPLOAD_PAGE[dataset])

@college_account_required
def college_departments(request):
    profile = request.user.college_profile
    departments = _department_summary_rows(profile)
    ctx = _page_ctx(profile, COLLEGE_NAV, "Department Overview", "Department Overview",
                    f"{len(departments)} departments", "College Admin", departments=departments)
    return render(request, "portal/college_departments.html", ctx)


def _college_student_rows(profile):
    rows = []
    admin_records_by_name = _admin_student_records_by_name(profile)
    for student in StudentProfile.objects.select_related("user").filter(college=profile).order_by("user__first_name", "user__last_name", "user__username"):
        student_name = (student.user.get_full_name() or student.user.username).strip().casefold()
        matching_records = admin_records_by_name.get(student_name, [])
        matching_record = matching_records.pop(0) if matching_records else None
        rows.append({
            "pk": f"student-profile:{student.pk}",
            "name": student.user.get_full_name() or student.user.username,
            "department": _canonical_department_name(
                student.department or (matching_record.department if matching_record else "")
            ) or "Unassigned",
            "avg_score": 0,
            "attendance_pct": 0,
            "read_only": True,
            "student_account": True,
            "username": student.user.username,
            "email": student.user.email or "—",
        })
    for record in profile.students.all():
        rows.append({
            "pk": record.pk,
            "name": record.name,
            "department": _canonical_department_name(record.department),
            "avg_score": record.avg_score,
            "attendance_pct": record.attendance_pct,
            "read_only": False,
            "student_account": False,
        })
    rows.sort(key=lambda item: item["name"].casefold())
    return rows


@college_account_required
def college_students(request):
    profile = request.user.college_profile
    account_form = CollegeStudentAccountForm()
    if request.method == "POST" and request.POST.get("action") == "create_account":
        account_form = CollegeStudentAccountForm(request.POST)
        if account_form.is_valid():
            data = account_form.cleaned_data
            with transaction.atomic():
                user = User.objects.create_user(
                    username=data["username"],
                    password=data["password"],
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    email=data["email"],
                    is_active=True,
                )
                StudentProfile.objects.create(user=user, college=profile, department=data["department"])
                AdminStudentRecord.objects.create(
                    name=user.get_full_name() or user.username,
                    college_name=profile.college_name,
                    department=data["department"],
                    status="Active",
                )
            messages.success(request, f"Student account '{user.username}' was created for {profile.college_name}.")
            return redirect("college_students")
    students = _college_student_rows(profile)
    raw_department_options = {_canonical_department_name(student["department"]) for student in students if student["department"] != "—" and student["department"]}
    department_options = sorted(raw_department_options, key=_department_sort_key)
    selected_department = _canonical_department_name(request.GET.get("department", "").strip())
    if selected_department and selected_department not in department_options:
        selected_department = ""
    if selected_department and selected_department in department_options:
        students = [student for student in students if _canonical_department_name(student["department"]) == selected_department]
    elif selected_department:
        selected_department = ""
    student_groups = []
    for department in department_options:
        department_students = [student for student in students if student["department"] == department]
        if department_students:
            student_groups.append({"name": department, "students": department_students})
    management = _college_record_context(request, profile, CollegeStudent, CollegeStudentForm, "college_students")
    if not isinstance(management, dict):
        return management
    ctx = _page_ctx(profile, COLLEGE_NAV, "Student Performance", "Student Performance",
                    f"{len(students)} students tracked", "College Admin", students=students,
                    student_groups=student_groups, department_options=department_options,
                    selected_department=selected_department, account_form=account_form,
                    csv_dataset="students", **management)
    return render(request, "portal/college_students.html", ctx)


@college_account_required
def college_assessments(request):
    profile = request.user.college_profile
    assessments = profile.assessments.all()
    management = _college_record_context(request, profile, CollegeAssessment, CollegeAssessmentForm, "college_assessments")
    if not isinstance(management, dict):
        return management
    ctx = _page_ctx(profile, COLLEGE_NAV, "Assessments", "Assessments",
                    f"{assessments.count()} assessments", "College Admin", assessments=assessments,
                    csv_dataset="assessments", **management)
    return render(request, "portal/college_assessments.html", ctx)


@college_account_required
def college_attendance(request):
    profile = request.user.college_profile
    departments = _department_summary_rows(profile)
    management = _college_record_context(request, profile, Department, DepartmentAttendanceForm, "college_attendance")
    if not isinstance(management, dict):
        return management
    total_students = sum(d.total_students for d in departments) or 1
    avg_attendance = round(sum(float(d.attendance_pct) * d.total_students for d in departments) / total_students, 1) if departments else 0
    trend = profile.trend_points.all()
    trend_json = json.dumps({"labels": [t.month_label for t in trend], "values": [float(t.avg_percentage) for t in trend]})
    ctx = _page_ctx(profile, COLLEGE_NAV, "Attendance", "Attendance",
                    f"{avg_attendance}% average attendance", "College Admin",
                    departments=departments, avg_attendance=avg_attendance, trend_json=trend_json,
                    csv_dataset="attendance", **management)
    return render(request, "portal/college_attendance.html", ctx)


@college_account_required
def college_programs(request):
    profile = request.user.college_profile
    programs = profile.programs.all()
    edit_program = programs.filter(pk=request.GET.get("edit")).first() if request.GET.get("edit") else None
    form_values = {
        "name": edit_program.name if edit_program else "",
        "students_count": edit_program.students_count if edit_program else 0,
        "status": edit_program.status if edit_program else "active",
    }

    if request.method == "POST":
        form_values = {
            "name": request.POST.get("name", "").strip(),
            "students_count": request.POST.get("students_count", "").strip(),
            "status": request.POST.get("status", "active").strip(),
        }
        program_id = request.POST.get("program_id", "").strip()
        target = programs.filter(pk=program_id).first() if program_id else CollegeProgram(college=profile)
        errors = []
        if target is None:
            errors.append("That program was not found for your college.")
        if not form_values["name"]:
            errors.append("Program name is required.")
        elif len(form_values["name"]) > 150:
            errors.append("Program name must be 150 characters or fewer.")
        try:
            student_count = int(form_values["students_count"])
            if student_count < 0:
                errors.append("Student count cannot be negative.")
        except ValueError:
            student_count = 0
            errors.append("Enter a valid student count.")
        if form_values["status"] not in dict(CollegeProgram.STATUS_CHOICES):
            errors.append("Choose a valid program status.")

        if errors:
            for error in errors:
                messages.error(request, error)
            edit_program = target
        else:
            target.name = form_values["name"]
            target.students_count = student_count
            target.status = form_values["status"]
            target.save()
            messages.success(request, "Program updated." if program_id else "Program created.")
            return redirect("college_programs")

    ctx = _page_ctx(profile, COLLEGE_NAV, "Training Programs", "Training Programs",
                    f"{programs.count()} programs", "College Admin", programs=programs,
                    edit_program=edit_program, form_values=form_values,
                    status_choices=CollegeProgram.STATUS_CHOICES, csv_dataset="programs")
    return render(request, "portal/college_programs.html", ctx)


@college_account_required
def college_payments(request):
    profile = request.user.college_profile
    invoices = AdminInvoice.objects.filter(college_name__iexact=profile.college_name).order_by("-issued_date")
    record_id = request.POST.get("record_id", "").strip() if request.method == "POST" else request.GET.get("edit", "")
    edit_invoice = invoices.filter(pk=record_id).first() if record_id else None
    payment_form = CollegeInvoiceForm(instance=edit_invoice)
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            if edit_invoice:
                edit_invoice.delete()
                messages.success(request, "Invoice deleted.")
            else:
                messages.error(request, "That invoice was not found for your college.")
            return redirect("college_payments")
        payment_form = CollegeInvoiceForm(request.POST, instance=edit_invoice)
        if payment_form.is_valid():
            invoice = payment_form.save(commit=False)
            invoice.college_name = profile.college_name
            invoice.save()
            messages.success(request, "Invoice updated." if edit_invoice else "Invoice created.")
            return redirect("college_payments")
    outstanding = sum(invoice.amount for invoice in invoices if invoice.status in {"due", "overdue"})
    ctx = _page_ctx(profile, COLLEGE_NAV, "Payments", "Payments",
                    f"{invoices.count()} invoices · outstanding ₹{outstanding}", "College Admin",
                    invoices=invoices, payment_form=payment_form, edit_invoice=edit_invoice,
                    csv_dataset="payments")
    return render(request, "portal/college_payments.html", ctx)


@college_account_required
def college_placements(request):
    profile = request.user.college_profile
    placements = profile.placements.all()
    management = _college_record_context(request, profile, PlacementRecord, PlacementRecordForm, "college_placements")
    if not isinstance(management, dict):
        return management
    total_placed = sum(p.students_placed for p in placements)
    ctx = _page_ctx(profile, COLLEGE_NAV, "Placements", "Placements",
                    f"{total_placed} students placed so far", "College Admin",
                    placements=placements, total_placed=total_placed,
                    csv_dataset="placements", **management)
    return render(request, "portal/college_placements.html", ctx)


@college_account_required
def college_reports(request):
    profile = request.user.college_profile
    quick_reports = profile.quick_reports.all()
    management = _college_record_context(request, profile, CollegeQuickReport, CollegeQuickReportForm, "college_reports")
    if not isinstance(management, dict):
        return management
    ctx = _page_ctx(profile, COLLEGE_NAV, "Reports & Analytics", "Reports & Analytics",
                    "Download or view detailed reports", "College Admin", quick_reports=quick_reports,
                    csv_dataset="reports", **management)
    return render(request, "portal/college_reports.html", ctx)


@college_account_required
def college_faculty(request):
    profile = request.user.college_profile
    faculty = profile.faculty.all()
    syllabus_coverage = profile.syllabus_coverage.all()
    management = _college_record_context(request, profile, Faculty, FacultyForm, "college_faculty")
    if not isinstance(management, dict):
        return management
    ctx = _page_ctx(profile, COLLEGE_NAV, "Faculty Performance", "Faculty Performance",
                    f"{faculty.count()} faculty members", "College Admin", faculty=faculty,
                    syllabus_coverage=syllabus_coverage, csv_dataset="faculty", **management)
    return render(request, "portal/college_faculty.html", ctx)


@college_account_required
def college_syllabus(request):
    profile = request.user.college_profile
    coverage = profile.syllabus_coverage.all()
    management = _college_record_context(request, profile, SyllabusCoverage, SyllabusCoverageForm, "college_syllabus")
    if not isinstance(management, dict):
        return management
    ctx = _page_ctx(profile, COLLEGE_NAV, "Syllabus Coverage", "Syllabus Coverage",
                    f"{coverage.count()} subjects tracked", "College Admin", coverage=coverage,
                    csv_dataset="syllabus", **management)
    return render(request, "portal/college_syllabus.html", ctx)


@college_account_required
def college_notifications(request):
    profile = request.user.college_profile
    notifications = profile.notifications.all()
    notifications.filter(is_read=False).update(is_read=True)
    ctx = _page_ctx(profile, COLLEGE_NAV, "Notifications", "Notifications",
                    "Recent platform notifications", "College Admin", notifications=notifications)
    return render(request, "portal/college_notifications.html", ctx)


@college_account_required
def college_settings(request):
    profile = request.user.college_profile
    if request.method == "POST":
        profile.college_name = request.POST.get("college_name", profile.college_name).strip()
        profile.location = request.POST.get("location", profile.location).strip()
        profile.academic_year = request.POST.get("academic_year", profile.academic_year).strip()
        profile.semester_label = request.POST.get("semester_label", profile.semester_label).strip()
        profile.save()
        messages.success(request, "Settings updated successfully.")
        return redirect("college_settings")
    ctx = _page_ctx(profile, COLLEGE_NAV, "Settings", "Settings", "Manage your college profile", "College Admin")
    return render(request, "portal/college_settings.html", ctx)


# =========================================================
# TRAINER — sub-pages
# =========================================================

@login_required
def trainer_batches(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    batches = profile.batches.all()
    ctx = _page_ctx(profile, TRAINER_NAV, "My Batches", "My Batches",
                    f"{batches.count()} active batches", "Trainer", batches=batches)
    return render(request, "portal/trainer_batches.html", ctx)


@login_required
def trainer_attendance(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    batches = profile.batches.all()
    entries = BatchAttendanceEntry.objects.filter(batch__trainer=profile).select_related("batch")
    ctx = _page_ctx(profile, TRAINER_NAV, "Attendance", "Attendance",
                    "Attendance across all your batches", "Trainer", batches=batches, entries=entries)
    return render(request, "portal/trainer_attendance.html", ctx)


@trainer_account_required
def trainer_assessments(request):
    profile = request.user.trainer_profile
    assessments = profile.assessments.all()
    tests = profile.online_tests.all()
    colleges = CollegeProfile.objects.filter(user__admin_profile__isnull=True, user__is_staff=False)
    schedule_form = OnlineTestForm()
    schedule_form.fields["college"].queryset = colleges
    errors = []

    if request.method == "POST":
        schedule_form = OnlineTestForm(request.POST)
        schedule_form.fields["college"].queryset = colleges
        prompts = request.POST.getlist("question_prompt")
        types = request.POST.getlist("question_type")
        options_rows = request.POST.getlist("question_options")
        answers_rows = request.POST.getlist("question_answers")
        points_rows = request.POST.getlist("question_points")
        question_rows = []
        if not schedule_form.is_valid():
            errors.extend(f"{field}: {error}" for field, field_errors in schedule_form.errors.items() for error in field_errors)
        is_external_assessment = bool(request.POST.get("external_url", "").strip())
        if not is_external_assessment and (not prompts or not any(prompt.strip() for prompt in prompts)):
            errors.append("Add at least one question.")

        for index, prompt in enumerate(prompts):
            prompt = prompt.strip()
            if not prompt and not (options_rows[index] if index < len(options_rows) else "").strip() and not (answers_rows[index] if index < len(answers_rows) else "").strip():
                continue
            question_type = types[index] if index < len(types) else ""
            options = [line.strip() for line in (options_rows[index] if index < len(options_rows) else "").splitlines() if line.strip()]
            correct_answers = [line.strip() for line in (answers_rows[index] if index < len(answers_rows) else "").splitlines() if line.strip()]
            try:
                points = int(points_rows[index]) if index < len(points_rows) and points_rows[index] else 1
            except ValueError:
                points = 0
            if not prompt:
                errors.append(f"Question {index + 1}: question text is required.")
            if question_type not in {choice[0] for choice in OnlineTestQuestion.TYPE_CHOICES}:
                errors.append(f"Question {index + 1}: choose a supported question type.")
            if points < 1 or points > 100:
                errors.append(f"Question {index + 1}: points must be between 1 and 100.")
            if question_type in {"single", "multiple", "matching"} and len(options) < 2:
                errors.append(f"Question {index + 1}: add at least two options or items, one per line.")
            if question_type in {"single", "true_false", "short", "multiple", "fill_blank", "numeric", "matching"} and not correct_answers:
                errors.append(f"Question {index + 1}: add at least one correct answer, one per line.")
            if question_type == "single" and len(correct_answers) != 1:
                errors.append(f"Question {index + 1}: multiple choice needs exactly one correct answer.")
            if question_type in {"single", "multiple"} and any(answer not in options for answer in correct_answers):
                errors.append(f"Question {index + 1}: each correct answer must exactly match an option.")
            if question_type == "matching" and (len(correct_answers) != len(options) or set(correct_answers) != set(options)):
                errors.append(f"Question {index + 1}: the correct order must contain each item exactly once.")
            if question_type == "true_false":
                options = ["True", "False"]
                correct_answers = [answer.title() for answer in correct_answers]
                if any(answer not in options for answer in correct_answers):
                    errors.append(f"Question {index + 1}: true/false answer must be True or False.")
            question_rows.append({
                "prompt": prompt, "question_type": question_type,
                "options": options, "correct_answers": correct_answers,
                "points": points,
            })

        if len(question_rows) != len([prompt for prompt in prompts if prompt.strip()]):
            errors.append("Complete or remove each partially filled question row.")

        if not errors and schedule_form.is_valid():
            with transaction.atomic():
                online_test = schedule_form.save(commit=False)
                online_test.trainer = profile
                online_test.save()
                for index, question in enumerate(question_rows):
                    OnlineTestQuestion.objects.create(test=online_test, order=index, **question)
            messages.success(request, "Test scheduled and published to students.")
            return redirect("trainer_test_results", test_id=online_test.pk)

    ctx = _page_ctx(profile, TRAINER_NAV, "Assessments", "Assessments",
                    f"{tests.count()} online tests · {assessments.count()} score summaries",
                    "Trainer", assessments=assessments, tests=tests,
                    schedule_form=schedule_form, question_types=OnlineTestQuestion.TYPE_CHOICES,
                    creation_errors=errors, colleges=colleges)
    return render(request, "portal/trainer_assessments.html", ctx)


@trainer_account_required
def trainer_test_results(request, test_id):
    trainer = request.user.trainer_profile
    online_test = get_object_or_404(trainer.online_tests.prefetch_related("questions", "attempts__student__user"), pk=test_id)
    now = timezone.now()
    results_available = now >= online_test.closes_at
    attempts = online_test.attempts.select_related("student__user").prefetch_related("answers__question")
    ctx = _page_ctx(
        trainer, TRAINER_NAV, "Assessments", online_test.title,
        "Student results" if results_available else "Results will be released after the scheduled end time.",
        "Trainer", online_test=online_test, attempts=attempts,
        results_available=results_available,
    )
    return render(request, "portal/trainer_test_results.html", ctx)


@trainer_account_required
def trainer_review_test_answer(request, test_id, answer_id):
    trainer = request.user.trainer_profile
    online_test = get_object_or_404(trainer.online_tests, pk=test_id)
    if timezone.now() < online_test.closes_at:
        return HttpResponseForbidden("Answers can only be reviewed after the test closes.")
    answer = get_object_or_404(
        OnlineTestAnswer.objects.select_related("attempt", "question"),
        pk=answer_id, attempt__test=online_test,
    )
    if answer.question.question_type not in {"essay", "file"}:
        return HttpResponseForbidden("Only written and file responses need manual review.")
    if request.method == "POST":
        try:
            points = int(request.POST.get("points_awarded", ""))
        except ValueError:
            points = -1
        if points < 0 or points > answer.question.points:
            messages.error(request, f"Score must be between 0 and {answer.question.points}.")
        else:
            answer.points_awarded = points
            answer.reviewed = True
            answer.save(update_fields=["points_awarded", "reviewed"])
            attempt = answer.attempt
            attempt.pending_manual_review = attempt.answers.filter(
                question__question_type__in=["essay", "file"], reviewed=False,
            ).count()
            attempt.score = sum(a.points_awarded for a in attempt.answers.all())
            attempt.save(update_fields=["pending_manual_review", "score"])
            messages.success(request, "Written response scored.")
        return redirect("trainer_test_results", test_id=online_test.pk)
    return HttpResponseForbidden("Submit a score to review this written response.")


@login_required
def trainer_assignments(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    assignments = profile.assignments.all()
    ctx = _page_ctx(profile, TRAINER_NAV, "Assignments", "Assignments",
                    f"{assignments.count()} assignments uploaded", "Trainer", assignments=assignments)
    return render(request, "portal/trainer_assignments.html", ctx)


@login_required
def trainer_students(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    if profile.college_id is None:
        students = StudentProfile.objects.none()
    else:
        students = StudentProfile.objects.select_related("user", "college").filter(college=profile.college).order_by(
            "user__first_name", "user__last_name", "user__username"
        )
    ctx = _page_ctx(profile, TRAINER_NAV, "Student Performance", "Student Performance",
                    f"{students.count()} students in {profile.college.college_name if profile.college else 'your college'}",
                    "Trainer", students=students)
    return render(request, "portal/trainer_students.html", ctx)


@login_required
def trainer_question_bank(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    items = profile.question_bank.all()
    ctx = _page_ctx(profile, TRAINER_NAV, "Question Bank", "Question Bank",
                    f"{items.count()} topics available", "Trainer", items=items)
    return render(request, "portal/trainer_question_bank.html", ctx)


@login_required
def trainer_reports(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    trend = profile.trend_points.all()
    trend_json = json.dumps({"labels": [t.month_label for t in trend], "values": [float(t.avg_percentage) for t in trend]})
    ctx = _page_ctx(profile, TRAINER_NAV, "Reports", "Reports",
                    "Your training performance reports", "Trainer", trend_json=trend_json)
    return render(request, "portal/trainer_reports.html", ctx)


@login_required
def trainer_calendar(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    events = profile.calendar_events.all()
    ctx = _page_ctx(profile, TRAINER_NAV, "Training Calendar", "Training Calendar",
                    "Upcoming sessions across your batches", "Trainer", events=events)
    return render(request, "portal/trainer_calendar.html", ctx)


@login_required
def trainer_settings(request):
    profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
    user = profile.user
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "availability":
            raw_date = request.POST.get("availability_date", "").strip()
            if not raw_date:
                messages.error(request, "Please choose a date for availability.")
                return redirect("trainer_settings")
            try:
                availability_date = date.fromisoformat(raw_date)
            except ValueError:
                messages.error(request, "The selected availability date is invalid.")
                return redirect("trainer_settings")
            availability, _ = TrainerAvailability.objects.get_or_create(trainer=profile, date=availability_date)
            availability.is_available = request.POST.get("is_available") not in {"false", "0", "no", "No"}
            availability.note = request.POST.get("availability_note", "").strip()
            availability.save()
            messages.success(request, "Availability updated successfully.")
            return redirect("trainer_settings")

        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.last_name = request.POST.get("last_name", user.last_name).strip()
        user.email = request.POST.get("email", user.email).strip()
        user.save()
        messages.success(request, "Settings updated successfully.")
        return redirect("trainer_settings")

    availability_entries = profile.availability.order_by("date")
    ctx = _page_ctx(profile, TRAINER_NAV, "Settings", "Settings", "Manage your trainer account", "Trainer",
                    availability_entries=availability_entries)
    return render(request, "portal/trainer_settings.html", ctx)


# =========================================================
# COMPANY — sub-pages
# =========================================================

@login_required
def company_search(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    candidates = profile.candidates.all()

    dept = request.GET.get("department", "").strip()
    min_score = request.GET.get("min_score", "").strip()
    if dept:
        candidates = candidates.filter(department__iexact=dept)
    if min_score.isdigit():
        candidates = [c for c in candidates if c.overall_score >= int(min_score)]

    all_departments = sorted(set(c.department for c in profile.candidates.all()))
    ctx = _page_ctx(profile, COMPANY_NAV, "Search Students", "Search Students",
                    "Filter and find the right candidates", "Company / HR",
                    candidates=candidates, all_departments=all_departments,
                    selected_department=dept, min_score=min_score)
    return render(request, "portal/company_search.html", ctx)


@login_required
def company_shortlisted(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    candidates = profile.candidates.filter(shortlist_status="shortlisted")
    ctx = _page_ctx(profile, COMPANY_NAV, "Shortlisted Candidates", "Shortlisted Candidates",
                    f"{candidates.count()} candidates shortlisted", "Company / HR", candidates=candidates)
    return render(request, "portal/company_shortlisted.html", ctx)


@login_required
def company_interviews(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    interviews = profile.interviews.all()
    ctx = _page_ctx(profile, COMPANY_NAV, "Interviews", "Interviews",
                    f"{interviews.count()} interviews total", "Company / HR", interviews=interviews)
    return render(request, "portal/company_interviews.html", ctx)


@login_required
def company_drives(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    drives = profile.job_drives.all()
    ctx = _page_ctx(profile, COMPANY_NAV, "Job Drives", "Job Drives",
                    f"{drives.count()} drives", "Company / HR", drives=drives)
    return render(request, "portal/company_drives.html", ctx)


@login_required
def company_offers(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    offers = profile.offers.all()
    ctx = _page_ctx(profile, COMPANY_NAV, "Offers", "Offers",
                    f"{offers.count()} offers extended", "Company / HR", offers=offers)
    return render(request, "portal/company_offers.html", ctx)


@login_required
def company_reports(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    candidates = profile.candidates.all()
    interviews = profile.interviews.all()
    ctx = _page_ctx(profile, COMPANY_NAV, "Reports", "Reports",
                    "Your hiring pipeline at a glance", "Company / HR",
                    total_candidates=candidates.count(), total_interviews=interviews.count(),
                    hired=profile.hired)
    return render(request, "portal/company_reports.html", ctx)


@login_required
def company_profile_view(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.company_name = request.POST.get("company_name", profile.company_name).strip()
        profile.save()
        messages.success(request, "Company profile updated successfully.")
        return redirect("company_profile")
    ctx = _page_ctx(profile, COMPANY_NAV, "Company Profile", "Company Profile",
                    "Manage your company details", "Company / HR")
    return render(request, "portal/company_profile.html", ctx)


@login_required
def company_settings(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    user = profile.user
    if request.method == "POST":
        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.email = request.POST.get("email", user.email).strip()
        user.save()
        messages.success(request, "Settings updated successfully.")
        return redirect("company_settings")
    ctx = _page_ctx(profile, COMPANY_NAV, "Settings", "Settings", "Manage your account", "Company / HR")
    return render(request, "portal/company_settings.html", ctx)
