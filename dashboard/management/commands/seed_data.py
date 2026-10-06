from datetime import date, timedelta, time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from dashboard.models import (
    StudentProfile,
    Course,
    Enrollment,
    AttendanceRecord,
    Assessment,
    Strength,
    AreaToImprove,
    ActivityLog,
    Assignment,
    Certificate,
    Message,
    CalendarEvent,
    Payment,
    Skill,
)


class Command(BaseCommand):
    help = "Seed the database with demo data for the student dashboard."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username="ananya",
            defaults={"first_name": "Ananya", "last_name": "Sharma", "email": "ananya@example.com"},
        )
        if created:
            user.set_password("student123")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created user 'ananya' / password 'student123'"))
        else:
            self.stdout.write("User 'ananya' already exists, reusing it.")

        profile, _ = StudentProfile.objects.get_or_create(user=user)
        profile.semester_label = "Current Semester"
        profile.semester_range = "May - Aug 2025"
        profile.total_learning_hours = 146
        profile.save()

        # Clear old data for a clean reseed
        profile.enrollments.all().delete()
        profile.attendance_records.all().delete()
        profile.assessments.all().delete()
        profile.strengths.all().delete()
        profile.improvement_areas.all().delete()
        profile.activities.all().delete()
        profile.assignments.all().delete()
        profile.certificates.all().delete()
        profile.messages.all().delete()
        profile.events.all().delete()
        profile.payments.all().delete()
        profile.skills.all().delete()

        today = date.today()

        course_data = [
            ("Python Programming", "fa-brands fa-python", 85, 96, 12, 14),
            ("Web Development", "fa-solid fa-code", 78, 93, 10, 14),
            ("Data Science", "fa-solid fa-database", 72, 88, 9, 15),
            ("DBMS", "fa-solid fa-server", 68, 85, 7, 14),
            ("Aptitude & Reasoning", "fa-solid fa-brain", 81, 94, 8, 10),
            ("Soft Skills", "fa-solid fa-comments", 75, 90, 10, 10),
        ]
        courses = {}
        for name, icon, avg, high, done, total in course_data:
            course, _ = Course.objects.get_or_create(name=name, defaults={"icon_class": icon})
            courses[name] = course
            Enrollment.objects.create(
                student=profile,
                course=course,
                avg_score=avg,
                highest_score=high,
                modules_completed=done,
                modules_total=total,
                is_completed=(done == total),
            )

        attendance_data = [
            ("May", 1, 30, 27),
            ("Jun", 2, 32, 29),
            ("Jul", 3, 33, 31),
            ("Aug", 4, 30, 28),
        ]
        for month, order, total, present in attendance_data:
            absent = total - present - 1
            AttendanceRecord.objects.create(
                student=profile,
                month_label=month,
                order=order,
                total_classes=total,
                present=present,
                absent=max(absent, 0),
                late=1,
            )

        assessment_data = [
            ("Python Quiz 4", "Python", 92, date(2025, 8, 18), "completed"),
            ("Web Dev Test 3", "Web Dev", 78, date(2025, 8, 16), "completed"),
            ("DSA Mock Test", "Aptitude", 65, date(2025, 8, 12), "completed"),
            ("DBMS Quiz 2", "DBMS", 70, date(2025, 8, 10), "completed"),
            ("Python Project Test", "Python", 88, date(2025, 8, 8), "completed"),
            ("Data Science Basics", "Data Science", 74, date(2025, 8, 5), "completed"),
            ("Aptitude Test 3", "Aptitude", None, date(2025, 8, 25), "pending"),
            ("Soft Skills Review", "Soft Skills", None, date(2025, 8, 27), "pending"),
        ]
        for name, subject, score, dt, status in assessment_data:
            Assessment.objects.create(
                student=profile, name=name, subject=subject, score=score, date=dt, status=status
            )

        for title in ["Problem Solving", "Python Programming", "Logical Reasoning"]:
            Strength.objects.create(student=profile, title=title)

        for title in ["Database Concepts", "Advanced SQL", "Time Management"]:
            AreaToImprove.objects.create(student=profile, title=title)

        activity_data = [
            ("Submitted Web Development Assignment", "submit", "2025-08-18 10:30:00"),
            ("Completed Python Quiz 4", "complete", "2025-08-18 09:15:00"),
            ("Attended Live Class - Data Science", "attend", "2025-08-17 11:00:00"),
            ("Downloaded Study Material - DBMS", "download", "2025-08-16 16:45:00"),
        ]
        for desc, kind, ts in activity_data:
            ActivityLog.objects.create(
                student=profile, description=desc, activity_type=kind, timestamp=ts
            )

        assignment_data = [
            ("Python Mini Project", "Python Programming", today + timedelta(days=5), "in_progress", None),
            ("Portfolio Website", "Web Development", today + timedelta(days=8), "not_started", None),
            ("SQL Case Study", "DBMS", today - timedelta(days=3), "submitted", today - timedelta(days=4)),
            ("Data Cleaning Exercise", "Data Science", today - timedelta(days=10), "submitted", today - timedelta(days=11)),
        ]
        for title, course_name, due, status, submitted in assignment_data:
            Assignment.objects.create(
                student=profile,
                title=title,
                course=courses[course_name],
                due_date=due,
                status=status,
                submitted_date=submitted,
            )

        certificate_data = [
            ("Python Programming", today - timedelta(days=60), "TN-PY-2025-001"),
            ("Web Development", today - timedelta(days=120), "TN-WD-2025-014"),
            ("Digital Marketing", today - timedelta(days=200), "TN-DM-2025-032"),
        ]
        for title, issued, cred in certificate_data:
            Certificate.objects.create(
                student=profile, title=title, issuer="Transit Nexus", issued_date=issued, credential_id=cred
            )

        message_data = [
            ("Prof. Ramesh Kumar", "Instructor", "Great progress on your Python project!",
             "Your latest submission shows a strong grasp of OOP concepts. Keep it up.", today - timedelta(days=1)),
            ("Ms. Divya Iyer", "Instructor", "Web Development workshop rescheduled",
             "The workshop originally set for this week has moved to next Friday.", today - timedelta(days=2)),
            ("Support Team", "Admin", "Fee receipt generated",
             "Your payment receipt for this semester is now available for download.", today - timedelta(days=4)),
        ]
        for sender, role, subject, body, ts in message_data:
            Message.objects.create(
                student=profile, sender_name=sender, sender_role=role, subject=subject, body=body,
                timestamp=ts, is_read=False,
            )

        event_data = [
            ("Python - Live Session", "class", today + timedelta(days=2), time(10, 0), time(11, 30), "Prof. Ramesh Kumar"),
            ("Web Development Workshop", "workshop", today + timedelta(days=3), time(14, 0), time(16, 0), "Ms. Divya Iyer"),
            ("Data Science Basics", "class", today + timedelta(days=4), time(10, 0), time(11, 30), "Dr. Neha Kapoor"),
            ("DBMS Mid-Term Exam", "exam", today + timedelta(days=7), time(9, 0), time(11, 0), ""),
            ("Python Mini Project Due", "assignment", today + timedelta(days=5), None, None, ""),
        ]
        for title, etype, dt, start, end, instructor in event_data:
            CalendarEvent.objects.create(
                student=profile, title=title, event_type=etype, date=dt,
                start_time=start, end_time=end, instructor=instructor,
            )

        payment_data = [
            ("Semester Tuition Fee", 25000, today - timedelta(days=30), today - timedelta(days=28), "paid"),
            ("Lab & Material Fee", 3500, today - timedelta(days=30), today - timedelta(days=28), "paid"),
            ("Certification Exam Fee", 1500, today + timedelta(days=10), None, "due"),
        ]
        for desc, amount, due, paid, status in payment_data:
            Payment.objects.create(
                student=profile, description=desc, amount=amount, due_date=due, paid_date=paid, status=status
            )

        skill_data = [
            ("Python Programming", 88, "technical"),
            ("Problem Solving", 82, "aptitude"),
            ("Logical Reasoning", 79, "aptitude"),
            ("SQL & Databases", 62, "technical"),
            ("Communication", 75, "soft"),
            ("Teamwork", 85, "soft"),
        ]
        for name, pct, category in skill_data:
            Skill.objects.create(student=profile, name=name, proficiency_percent=pct, category=category)

        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))
