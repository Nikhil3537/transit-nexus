from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from dashboard.models import StudentProfile
from portal.models import CollegeProfile, CompanyProfile, TrainerProfile


class Command(BaseCommand):
    help = "Create a login account that stays inactive until an admin approves it."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")
        parser.add_argument(
            "role",
            choices=["student", "college", "trainer", "company"],
        )
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")
        parser.add_argument("--email", default="")

    def handle(self, *args, **options):
        username = options["username"]
        if User.objects.filter(username=username).exists():
            raise CommandError(f"Username '{username}' already exists.")

        user = User.objects.create_user(
            username=username,
            password=options["password"],
            first_name=options["first_name"],
            last_name=options["last_name"],
            email=options["email"],
            is_active=False,
        )

        role = options["role"]
        if role == "student":
            StudentProfile.objects.create(user=user)
        elif role == "college":
            CollegeProfile.objects.create(user=user)
        elif role == "trainer":
            TrainerProfile.objects.create(user=user)
        else:
            CompanyProfile.objects.create(user=user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created pending {role} account '{username}'. "
                "An administrator must enable Active in /admin/ before login."
            )
        )
