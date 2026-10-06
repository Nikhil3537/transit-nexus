import json
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import (
    StudentProfile,
    Assignment,
    Certificate,
    Message,
    CalendarEvent,
    Payment,
    Skill,
)
from portal.models import AdminStudentRecord, CollegeProfile, OnlineTest, OnlineTestAnswer, OnlineTestAttempt


def _redirect_for_role(user):
    """Send a freshly logged-in user to the dashboard that matches their role."""
    if hasattr(user, "admin_profile"):
        return redirect("admin_dashboard")
    if hasattr(user, "college_profile"):
        return redirect("college_dashboard")
    if hasattr(user, "trainer_profile"):
        return redirect("trainer_dashboard")
    if hasattr(user, "company_profile"):
        return redirect("company_dashboard")
    if hasattr(user, "profile") and getattr(user.profile, "college_id", None):
        return redirect("student_colleges")
    return redirect("dashboard")  # default: student


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_for_role(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return _redirect_for_role(user)
        if User.objects.filter(username=username, is_active=False).exists():
            messages.error(request, "This account is waiting for administrator approval.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "dashboard/login.html")


def student_register_view(request):
    if request.user.is_authenticated:
        return _redirect_for_role(request.user)

    colleges = list(
        CollegeProfile.objects.select_related("user").prefetch_related("departments").filter(
            user__admin_profile__isnull=True,
            user__is_staff=False,
            user__is_active=True,
        ).order_by("college_name", "pk")
    )
    departments_by_college = {}
    for college in colleges:
        department_names = {
            department.name.strip()
            for department in college.departments.all()
            if department.name and department.name.strip()
        }
        department_names.update(
            name.strip()
            for name in AdminStudentRecord.objects.filter(
                college_name__iexact=college.college_name,
            ).values_list("department", flat=True)
            if name and name.strip()
        )
        department_names.update(
            name.strip()
            for name in college.students.values_list("department", flat=True)
            if name and name.strip()
        )
        departments_by_college[str(college.pk)] = sorted(department_names, key=str.casefold)
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        college_id = request.POST.get("college_id", "").strip()
        department_name = request.POST.get("department_name", "").strip()
        college = next((item for item in colleges if str(item.pk) == college_id), None)
        valid_department_names = departments_by_college.get(str(college.pk), []) if college else []

        if not username or not password:
            messages.error(request, "Username and password are required.")
        elif college is None:
            messages.error(request, "Choose a college from the list.")
        elif department_name not in valid_department_names:
            messages.error(request, "Choose a department that belongs to the selected college.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=False,
            )
            StudentProfile.objects.create(user=user, college=college, department=department_name)
            AdminStudentRecord.objects.create(
                name=user.get_full_name() or user.username,
                college_name=college.college_name,
                department=department_name,
                status="Pending",
            )
            messages.success(request, "Your student account has been created successfully. Please wait for administrator approval.")
            return redirect("login")

    return render(request, "dashboard/student_register.html", {
        "form_values": {
            "college_id": request.POST.get("college_id", "").strip(),
            "department_name": request.POST.get("department_name", "").strip(),
        } if request.method == "POST" else {},
        "colleges": colleges,
        "departments_by_college": departments_by_college,
    })


def logout_view(request):
    logout(request)
    return redirect("login")


def _base_context(profile):
    """Common context every page needs (unread message badge, etc.)"""
    return {
        "profile": profile,
        "unread_message_count": profile.messages.filter(is_read=False).count(),
    }


@login_required
def student_colleges_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    colleges = [profile.college] if profile.college else []

    context = {
        **_base_context(profile),
        "active_page": "student_colleges",
        "page_title": "My College",
        "page_subtitle": "Your assigned college details",
        "colleges": colleges,
    }
    return render(request, "dashboard/student_colleges.html", context)


@login_required
def student_dashboard(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    colleges = [profile.college] if profile.college else []
    enrollments = profile.enrollments.select_related("course").all()
    attendance_records = list(profile.attendance_records.all())
    assessments = list(profile.assessments.all())
    strengths = profile.strengths.all()
    improvements = profile.improvement_areas.all()
    activities = profile.activities.all()[:6]

    # ---- Attendance summary ----
    total_classes = sum(a.total_classes for a in attendance_records)
    total_present = sum(a.present for a in attendance_records)
    total_absent = sum(a.absent for a in attendance_records)
    total_late = sum(a.late for a in attendance_records)
    overall_attendance = round((total_present / total_classes) * 100) if total_classes else 0

    attendance_trend = {
        "labels": [a.month_label for a in attendance_records],
        "values": [a.percentage for a in attendance_records],
    }

    # ---- Assessment summary ----
    completed_assessments = [a for a in assessments if a.status == "completed"]
    pending_assessments = [a for a in assessments if a.status == "pending"]
    scored = [a for a in completed_assessments if a.score is not None]
    average_score = round(sum(float(a.score) for a in scored) / len(scored), 1) if scored else 0

    buckets = {"Excellent": 0, "Good": 0, "Average": 0, "Needs Improvement": 0}
    for a in scored:
        buckets[a.performance_label] += 1
    total_scored = len(scored) or 1
    score_distribution = [
        {"label": k, "count": v, "pct": round(v / total_scored * 100)} for k, v in buckets.items()
    ]

    score_trend_source = sorted(scored, key=lambda a: a.date)[-4:]
    score_trend = {
        "labels": [a.date.strftime("%b") for a in score_trend_source],
        "values": [float(a.score) for a in score_trend_source],
    }

    # ---- Overall grade ----
    if average_score >= 90:
        overall_grade, grade_label = "A+", "Outstanding"
    elif average_score >= 80:
        overall_grade, grade_label = "A", "Very Good"
    elif average_score >= 70:
        overall_grade, grade_label = "B", "Good"
    elif average_score >= 50:
        overall_grade, grade_label = "C", "Average"
    else:
        overall_grade, grade_label = "D", "Needs Work"

    recent_assessments = assessments[:5]

    context = {
        **_base_context(profile),
        "active_page": "dashboard",
        "colleges": colleges,
        "enrollments": enrollments,
        "courses_enrolled": enrollments.count(),
        "overall_attendance": overall_attendance,
        "total_classes": total_classes,
        "total_present": total_present,
        "total_absent": total_absent,
        "total_late": total_late,
        "attendance_trend_json": json.dumps(attendance_trend),
        "assessments_taken": len(assessments),
        "assessments_completed": len(completed_assessments),
        "assessments_pending": len(pending_assessments),
        "average_score": average_score,
        "score_distribution": score_distribution,
        "score_trend_json": json.dumps(score_trend),
        "overall_grade": overall_grade,
        "grade_label": grade_label,
        "recent_assessments": recent_assessments,
        "strengths": strengths,
        "improvements": improvements,
        "activities": activities,
        "total_learning_hours": profile.total_learning_hours,
    }
    return render(request, "dashboard/student_dashboard.html", context)


@login_required
def profile_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    user = profile.user

    if request.method == "POST":
        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.last_name = request.POST.get("last_name", user.last_name).strip()
        user.email = request.POST.get("email", user.email).strip()
        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")

    context = {
        **_base_context(profile),
        "active_page": "profile",
        "page_title": "My Profile",
        "page_subtitle": "Manage your personal information",
        "courses_enrolled": profile.enrollments.count(),
        "certificates_count": profile.certificates.count(),
    }
    return render(request, "dashboard/profile.html", context)


@login_required
def courses_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    enrollments = profile.enrollments.select_related("course").all()
    context = {
        **_base_context(profile),
        "active_page": "courses",
        "page_title": "My Courses",
        "page_subtitle": f"You are enrolled in {enrollments.count()} courses",
        "enrollments": enrollments,
    }
    return render(request, "dashboard/courses.html", context)


@login_required
def live_classes_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    events = profile.events.filter(event_type="class")
    upcoming = events.filter(date__gte=today)
    past = events.filter(date__lt=today)
    context = {
        **_base_context(profile),
        "active_page": "live_classes",
        "page_title": "Live Classes",
        "page_subtitle": "Join scheduled sessions with your instructors",
        "upcoming": upcoming,
        "past": past,
    }
    return render(request, "dashboard/live_classes.html", context)


@login_required
def attendance_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    records = list(profile.attendance_records.all())
    total_classes = sum(a.total_classes for a in records)
    total_present = sum(a.present for a in records)
    total_absent = sum(a.absent for a in records)
    total_late = sum(a.late for a in records)
    overall_attendance = round((total_present / total_classes) * 100) if total_classes else 0

    trend = {
        "labels": [a.month_label for a in records],
        "values": [a.percentage for a in records],
    }

    context = {
        **_base_context(profile),
        "active_page": "attendance",
        "page_title": "My Attendance",
        "page_subtitle": "Track your attendance across all courses",
        "records": records,
        "total_classes": total_classes,
        "total_present": total_present,
        "total_absent": total_absent,
        "total_late": total_late,
        "overall_attendance": overall_attendance,
        "trend_json": json.dumps(trend),
    }
    return render(request, "dashboard/attendance.html", context)


@login_required
def assessments_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    assessments = profile.assessments.all()
    completed = assessments.filter(status="completed")
    pending = assessments.filter(status="pending")
    context = {
        **_base_context(profile),
        "active_page": "assessments",
        "page_title": "Assessments",
        "page_subtitle": f"{completed.count()} completed &middot; {pending.count()} pending",
        "assessments": assessments,
    }
    return render(request, "dashboard/assessments.html", context)


@login_required
def trainer_directory_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    from portal.models import TrainerAvailability, TrainerProfile

    query = request.GET.get("q", "").strip()
    selected_date_raw = request.GET.get("date", "").strip()
    selected_date = None
    if selected_date_raw:
        try:
            selected_date = date.fromisoformat(selected_date_raw)
        except ValueError:
            selected_date = None

    trainers = TrainerProfile.objects.select_related("user", "college").all()
    if profile.college_id:
        trainers = trainers.filter(college=profile.college)

    trainers = list(trainers)
    if query:
        trainer_query = query.casefold()
        trainers = [
            trainer for trainer in trainers
            if trainer_query in (trainer.user.get_full_name() or "").casefold()
            or trainer_query in (trainer.user.username or "").casefold()
            or trainer_query in (trainer.user.email or "").casefold()
            or (trainer.college and trainer_query in trainer.college.college_name.casefold())
        ]

    if selected_date:
        availability_by_trainer = {
            item.trainer_id: item for item in TrainerAvailability.objects.filter(date=selected_date, trainer__in=trainers)
        }
        for trainer in trainers:
            availability = availability_by_trainer.get(trainer.pk)
            trainer.is_available_on_date = availability.is_available if availability else True
            trainer.availability_status = "Available" if trainer.is_available_on_date else "Not available"
            trainer.availability_note = availability.note if availability else "Open for booking"
    else:
        for trainer in trainers:
            trainer.is_available_on_date = True
            trainer.availability_status = "Available"
            trainer.availability_note = "Open for booking"

    context = {
        **_base_context(profile),
        "active_page": "trainers",
        "page_title": "Trainers",
        "page_subtitle": "Search and connect with available trainers",
        "trainers": trainers,
        "query": query,
        "selected_date": selected_date.isoformat() if selected_date else "",
        "trainer_count": len(trainers),
    }
    return render(request, "dashboard/trainers.html", context)


def _require_student(request):
    user = request.user
    return not (
        user.is_staff
        or hasattr(user, "admin_profile")
        or hasattr(user, "college_profile")
        or hasattr(user, "trainer_profile")
        or hasattr(user, "company_profile")
    ) and not user.is_anonymous


def _normalize_answer(value):
    return " ".join(str(value).strip().casefold().split())


def _answers_match(question, submitted):
    expected = [str(value).strip() for value in question.correct_answers]
    if question.question_type == "multiple":
        return {_normalize_answer(value) for value in expected} == {_normalize_answer(value) for value in submitted}
    if question.question_type == "matching":
        return [_normalize_answer(value) for value in expected] == [_normalize_answer(value) for value in submitted]
    if question.question_type == "numeric":
        for expected_value in expected:
            try:
                if Decimal(str(submitted[0])) == Decimal(expected_value):
                    return True
            except (InvalidOperation, IndexError):
                continue
        return False
    return len(submitted) == 1 and any(_normalize_answer(submitted[0]) == _normalize_answer(value) for value in expected)


@login_required
def scheduled_tests_view(request):
    if not _require_student(request):
        return HttpResponseForbidden("Student access is required.")
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    now = timezone.now()
    tests = OnlineTest.objects.select_related("trainer__user").prefetch_related("questions").filter(college=profile.college) if profile.college_id else OnlineTest.objects.none()
    attempts = {attempt.test_id: attempt for attempt in profile.online_test_attempts.select_related("test")}
    rows = [{"test": online_test, "attempt": attempts.get(online_test.pk)} for online_test in tests]
    context = {
        **_base_context(profile),
        "active_page": "scheduled_tests",
        "page_title": "Scheduled Tests",
        "page_subtitle": "Take scheduled assessments and review results after they close.",
        "test_rows": rows,
        "now": now,
    }
    return render(request, "dashboard/scheduled_tests.html", context)


@login_required
def take_online_test_view(request, test_id):
    if not _require_student(request):
        return HttpResponseForbidden("Student access is required.")
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    if profile.college_id is None:
        raise Http404("This student account is not assigned to a college.")
    online_test = get_object_or_404(
        OnlineTest.objects.select_related("trainer", "college").prefetch_related("questions"),
        pk=test_id, college=profile.college,
    )
    now = timezone.now()
    attempt = profile.online_test_attempts.filter(test=online_test).first()
    results_released = now >= online_test.closes_at
    available = online_test.opens_at <= now < online_test.closes_at
    if request.method == "GET" and attempt and attempt.status == "in_progress":
        deadline = min(attempt.started_at + timedelta(minutes=online_test.duration_minutes), online_test.closes_at)
        if now >= deadline:
            for question in online_test.questions.all():
                OnlineTestAnswer.objects.get_or_create(attempt=attempt, question=question)
            attempt.status = "submitted"
            attempt.submitted_at = deadline
            attempt.score = 0
            attempt.possible_points = sum(question.points for question in online_test.questions.all())
            attempt.pending_manual_review = 0
            attempt.save(update_fields=["status", "submitted_at", "score", "possible_points", "pending_manual_review"])

    if request.method == "POST":
        if attempt is None or attempt.status != "in_progress":
            return HttpResponseForbidden("There is no active attempt for this test.")
        deadline = min(attempt.started_at + timedelta(minutes=online_test.duration_minutes), online_test.closes_at)
        if now > deadline + timedelta(seconds=5):
            for question in online_test.questions.all():
                OnlineTestAnswer.objects.get_or_create(attempt=attempt, question=question)
            attempt.status = "submitted"
            attempt.submitted_at = deadline
            attempt.score = 0
            attempt.possible_points = sum(question.points for question in online_test.questions.all())
            attempt.pending_manual_review = 0
            attempt.save(update_fields=["status", "submitted_at", "score", "possible_points", "pending_manual_review"])
            messages.info(request, "The test deadline passed before submission. No late answers were accepted.")
            return redirect("take_online_test", test_id=online_test.pk)
        for question in online_test.questions.filter(question_type="file"):
            uploaded_file = request.FILES.get(f"answer_{question.pk}")
            if uploaded_file:
                suffix = uploaded_file.name.rsplit(".", 1)[-1].casefold() if "." in uploaded_file.name else ""
                if uploaded_file.size > 10 * 1024 * 1024 or suffix not in {"pdf", "png", "jpg", "jpeg", "doc", "docx"}:
                    messages.error(request, "File answers must be PDF, image, or Word files up to 10 MB.")
                    return redirect("take_online_test", test_id=online_test.pk)
        with transaction.atomic():
            earned = 0
            possible = 0
            manual_count = 0
            for question in online_test.questions.all():
                possible += question.points
                field_name = f"answer_{question.pk}"
                uploaded_file = None
                if question.question_type in {"single", "multiple", "true_false"}:
                    responses = request.POST.getlist(field_name)
                elif question.question_type == "file":
                    uploaded_file = request.FILES.get(field_name)
                    responses = [uploaded_file.name] if uploaded_file else []
                else:
                    value = request.POST.get(field_name, "").strip()
                    responses = [line.strip() for line in value.splitlines() if line.strip()] if question.question_type == "matching" else ([value] if value else [])
                answer = OnlineTestAnswer.objects.filter(attempt=attempt, question=question).first()
                if answer is None:
                    answer = OnlineTestAnswer(attempt=attempt, question=question)
                answer.response = responses
                if question.question_type in {"essay", "file"}:
                    answer.points_awarded = 0
                    answer.reviewed = False
                    if uploaded_file:
                        answer.uploaded_file = uploaded_file
                    if responses or uploaded_file:
                        manual_count += 1
                else:
                    is_correct = _answers_match(question, responses)
                    answer.points_awarded = question.points if is_correct else 0
                    answer.reviewed = True
                answer.save()
                earned += answer.points_awarded
            attempt.status = "submitted"
            attempt.submitted_at = min(now, deadline)
            attempt.score = earned
            attempt.possible_points = possible
            attempt.pending_manual_review = manual_count
            attempt.save(update_fields=["status", "submitted_at", "score", "possible_points", "pending_manual_review"])
        return redirect("take_online_test", test_id=online_test.pk)

    if attempt is None and available:
        attempt = OnlineTestAttempt.objects.create(test=online_test, student=profile)

    deadline = min(attempt.started_at + timedelta(minutes=online_test.duration_minutes), online_test.closes_at) if attempt and attempt.status == "in_progress" else None
    answers = {answer.question_id: answer for answer in attempt.answers.all()} if attempt else {}
    context = {
        **_base_context(profile),
        "active_page": "scheduled_tests",
        "online_test": online_test,
        "attempt": attempt,
        "available": available,
        "results_released": results_released,
        "now": now,
        "deadline": deadline,
        "answers": answers,
        "questions": online_test.questions.all(),
        "total_points": sum(question.points for question in online_test.questions.all()),
    }
    return render(request, "dashboard/take_online_test.html", context)


@login_required
def download_test_answer_file(request, answer_id):
    if not _require_student(request) and not hasattr(request.user, "trainer_profile"):
        return HttpResponseForbidden("Test participant access is required.")
    answer = get_object_or_404(
        OnlineTestAnswer.objects.select_related("attempt__student", "attempt__test__trainer"),
        pk=answer_id,
    )
    is_student_owner = hasattr(request.user, "profile") and answer.attempt.student.user_id == request.user.pk
    is_test_trainer = hasattr(request.user, "trainer_profile") and answer.attempt.test.trainer.user_id == request.user.pk
    if not (is_student_owner or is_test_trainer):
        return HttpResponseForbidden("You cannot access this answer file.")
    if not answer.uploaded_file:
        raise Http404("No file was uploaded for this answer.")
    if is_student_owner and timezone.now() < answer.attempt.test.closes_at:
        return HttpResponseForbidden("Answer files are available after the test closes.")
    return FileResponse(answer.uploaded_file.open("rb"), as_attachment=True, filename=answer.uploaded_file.name.rsplit("/", 1)[-1])


@login_required
def results_reports_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    enrollments = profile.enrollments.select_related("course").all()
    assessments = list(profile.assessments.filter(status="completed", score__isnull=False))

    trend_source = sorted(assessments, key=lambda a: a.date)[-6:]
    trend = {
        "labels": [a.date.strftime("%d %b") for a in trend_source],
        "values": [float(a.score) for a in trend_source],
    }
    avg_score = round(sum(float(a.score) for a in assessments) / len(assessments), 1) if assessments else 0

    context = {
        **_base_context(profile),
        "active_page": "results_reports",
        "page_title": "Results & Reports",
        "page_subtitle": "Your academic performance at a glance",
        "enrollments": enrollments,
        "avg_score": avg_score,
        "trend_json": json.dumps(trend),
    }
    return render(request, "dashboard/results_reports.html", context)


@login_required
def assignments_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    assignments = profile.assignments.select_related("course").all()
    context = {
        **_base_context(profile),
        "active_page": "assignments",
        "page_title": "Assignments",
        "page_subtitle": f"{assignments.filter(status='submitted').count()} submitted &middot; "
        f"{assignments.exclude(status='submitted').count()} pending",
        "assignments": assignments,
    }
    return render(request, "dashboard/assignments.html", context)


@login_required
def certificates_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    certificates = profile.certificates.all()
    context = {
        **_base_context(profile),
        "active_page": "certificates",
        "page_title": "Certificates",
        "page_subtitle": f"You have earned {certificates.count()} certificates",
        "certificates": certificates,
    }
    return render(request, "dashboard/certificates.html", context)


@login_required
def download_certificate_view(request, certificate_id):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    certificate = get_object_or_404(profile.certificates, pk=certificate_id)
    content = (
        "Transit Nexus Certificate\n\n"
        f"This certifies that {profile.user.get_full_name() or profile.user.username} "
        f"has earned {certificate.title}.\n"
        f"Issued by: {certificate.issuer}\n"
        f"Issued date: {certificate.issued_date:%d %b %Y}\n"
        f"Credential ID: {certificate.credential_id or 'Not assigned'}\n"
    )
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="certificate-{certificate.pk}.txt"'
    return response


@login_required
def learning_path_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    enrollments = profile.enrollments.select_related("course").all()
    context = {
        **_base_context(profile),
        "active_page": "learning_path",
        "page_title": "Learning Path",
        "page_subtitle": "Your roadmap across every enrolled course",
        "enrollments": enrollments,
    }
    return render(request, "dashboard/learning_path.html", context)


@login_required
def skill_progress_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    skills = profile.skills.all()
    strengths = profile.strengths.all()
    improvements = profile.improvement_areas.all()
    context = {
        **_base_context(profile),
        "active_page": "skill_progress",
        "page_title": "Skill Progress",
        "page_subtitle": "How your skills are developing over time",
        "skills": skills,
        "strengths": strengths,
        "improvements": improvements,
    }
    return render(request, "dashboard/skill_progress.html", context)


@login_required
def messages_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    message_list = profile.messages.all()
    # Mark all as read once the student opens the inbox
    message_list.filter(is_read=False).update(is_read=True)
    context = {
        **_base_context(profile),
        "active_page": "messages",
        "page_title": "Messages",
        "page_subtitle": "Conversations with instructors and support",
        "message_list": message_list,
        "unread_message_count": 0,
    }
    return render(request, "dashboard/messages.html", context)


@login_required
def calendar_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    events = profile.events.filter(date__gte=today)
    context = {
        **_base_context(profile),
        "active_page": "calendar",
        "page_title": "Calendar",
        "page_subtitle": "Upcoming classes, exams and deadlines",
        "events": events,
    }
    return render(request, "dashboard/calendar.html", context)


@login_required
def payments_view(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    payments = profile.payments.all()
    total_paid = sum(float(p.amount) for p in payments if p.status == "paid")
    total_due = sum(float(p.amount) for p in payments if p.status in ("due", "overdue"))
    context = {
        **_base_context(profile),
        "active_page": "payments",
        "page_title": "My Payments",
        "page_subtitle": "Fees, invoices and payment history",
        "payments": payments,
        "total_paid": total_paid,
        "total_due": total_due,
    }
    return render(request, "dashboard/payments.html", context)
