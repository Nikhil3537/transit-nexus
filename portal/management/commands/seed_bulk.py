from datetime import date, timedelta

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.models import Assessment, Course, Enrollment, StudentProfile
from portal.models import (
    AdminStudentRecord,
    Batch,
    Candidate,
    CollegeProfile,
    CompanyProfile,
    PartnerCollege,
    TrainerProfile,
)


class Command(BaseCommand):
    help = "Create repeatable bulk data for the Transit Nexus platform."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=500)
        parser.add_argument("--colleges", type=int, default=100)
        parser.add_argument("--trainers", type=int, default=100)
        parser.add_argument("--companies", type=int, default=100)

    @transaction.atomic
    def handle(self, *args, **options):
        students = options["students"]
        colleges = options["colleges"]
        trainers = options["trainers"]
        companies = options["companies"]
        student_password = make_password("student123")
        trainer_password = make_password("trainer123")
        company_password = make_password("company123")

        colleges_by_index = []
        for index in range(1, colleges + 1):
            name = f"Transit College {index:03d}"
            PartnerCollege.objects.update_or_create(
                name=name,
                defaults={
                    "students_count": max(1, students // max(colleges, 1)),
                    "active_programs": 4 + index % 7,
                    "pending_payment": (index % 5) * 25000,
                    "status": "payment_due" if index % 5 == 0 else "active",
                },
            )
            colleges_by_index.append(name)

        courses = [
            Course.objects.get_or_create(name=name, defaults={"icon_class": "fa-book"})[0]
            for name in [
                "Python Programming",
                "Web Development",
                "Data Science",
                "DBMS",
                "Aptitude & Reasoning",
                "Soft Skills",
            ]
        ]

        for index in range(1, students + 1):
            username = f"student_{index:04d}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": f"Student{index:04d}",
                    "last_name": "Nexus",
                    "email": f"{username}@example.com",
                },
            )
            if created:
                user.password = student_password
                user.save(update_fields=["password"])

            profile, _ = StudentProfile.objects.get_or_create(user=user)
            profile.semester_label = "Current Semester"
            profile.total_learning_hours = 40 + (index % 120)
            profile.save(update_fields=["semester_label", "total_learning_hours"])

            course = courses[(index - 1) % len(courses)]
            Enrollment.objects.update_or_create(
                student=profile,
                course=course,
                defaults={
                    "avg_score": 60 + (index % 40),
                    "highest_score": 70 + (index % 30),
                    "modules_completed": 4 + (index % 10),
                    "modules_total": 14,
                    "is_completed": index % 10 == 0,
                },
            )
            Assessment.objects.update_or_create(
                student=profile,
                name="Initial Skills Assessment",
                defaults={
                    "subject": course.name,
                    "score": 60 + (index % 40),
                    "date": date.today() - timedelta(days=index % 90),
                    "status": "completed",
                },
            )
            AdminStudentRecord.objects.update_or_create(
                name=f"Student{index:04d} Nexus",
                defaults={
                    "college_name": colleges_by_index[(index - 1) % len(colleges_by_index)],
                    "department": ["CSE", "ISE", "ECE", "ME", "AI&DS"][index % 5],
                    "performance_pct": 60 + (index % 40),
                    "status": "Active",
                },
            )

        for index in range(1, trainers + 1):
            username = f"trainer_{index:04d}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": f"Trainer{index:04d}",
                    "last_name": "Nexus",
                    "email": f"{username}@example.com",
                },
            )
            if created:
                user.password = trainer_password
                user.save(update_fields=["password"])
            profile, _ = TrainerProfile.objects.get_or_create(user=user)
            profile.assessments_created = 5 + index % 12
            profile.assignments_uploaded = 3 + index % 8
            profile.save(update_fields=["assessments_created", "assignments_uploaded"])
            Batch.objects.update_or_create(
                trainer=profile,
                name=f"Batch {index:04d}",
                defaults={
                    "total_students": 25 + index % 26,
                    "present_count": 20 + index % 20,
                    "absent_count": 5,
                },
            )

        for index in range(1, companies + 1):
            username = f"company_{index:04d}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": f"Company{index:04d}",
                    "last_name": "HR",
                    "email": f"{username}@example.com",
                },
            )
            if created:
                user.password = company_password
                user.save(update_fields=["password"])
            profile, _ = CompanyProfile.objects.get_or_create(user=user)
            profile.company_name = f"Nexus Company {index:03d}"
            profile.total_drives = 1 + index % 8
            profile.hired = index % 20
            profile.save(update_fields=["company_name", "total_drives", "hired"])
            Candidate.objects.update_or_create(
                company=profile,
                name=f"Candidate {index:04d}",
                defaults={
                    "department": ["CSE", "ISE", "ECE", "AI&DS"][index % 4],
                    "aptitude_score": 55 + index % 46,
                    "technical_score": 60 + index % 41,
                    "communication_score": 65 + index % 36,
                    "shortlist_status": "shortlisted" if index % 3 == 0 else "under_review",
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Bulk data ready: {students} students, {colleges} colleges, "
                f"{trainers} trainers, {companies} companies."
            )
        )
        self.stdout.write("Shared passwords: students student123, trainers trainer123, companies company123")
