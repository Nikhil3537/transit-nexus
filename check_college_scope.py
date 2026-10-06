import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "transit_nexus.settings")
import django
django.setup()
from django.contrib.auth.models import User
from dashboard.models import StudentProfile
from portal.models import CollegeProfile, TrainerProfile

college = CollegeProfile.objects.filter(college_name__iexact="ABC Engineering College").first()
if college is None:
    raise SystemExit("No college found: ABC Engineering College")

student_user = User.objects.filter(username="ananya").first()
if student_user is None:
    student_user = User.objects.create_user(
        username="ananya",
        password="student123",
        first_name="Ananya",
        last_name="Student",
        email="ananya@example.com",
        is_active=True,
    )
student_profile, _ = StudentProfile.objects.get_or_create(user=student_user)
student_profile.college = college
student_profile.save()

trainer_user = User.objects.filter(username="trainer_demo").first()
if trainer_user is None:
    trainer_user = User.objects.create_user(
        username="trainer_demo",
        password="trainer123",
        first_name="Demo",
        last_name="Trainer",
        email="trainer@example.com",
        is_active=True,
    )
trainer_profile, _ = TrainerProfile.objects.get_or_create(user=trainer_user)
trainer_profile.college = college
trainer_profile.save()

print("student", student_profile.user.username, student_profile.college.college_name)
print("trainer", trainer_profile.user.username, trainer_profile.college.college_name)
print("match_count", StudentProfile.objects.filter(college=college).count())
