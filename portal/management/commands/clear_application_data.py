from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps

from portal.models import AdminProfile


class Command(BaseCommand):
    help = "Delete application data while preserving administrator login accounts."

    @transaction.atomic
    def handle(self, *args, **options):
        for app_label in ("dashboard", "portal"):
            models = list(apps.get_app_config(app_label).get_models())
            for model in reversed(models):
                model.objects.all().delete()

        User.objects.exclude(is_superuser=True).exclude(username="Transit_admin").delete()

        admin_user = User.objects.filter(username="Transit_admin").first()
        if admin_user:
            AdminProfile.objects.update_or_create(
                user=admin_user,
                defaults={
                    "active_trainings": 0,
                    "assessments_conducted": 0,
                    "open_issues": 0,
                    "colleges_onboarded_this_month": 0,
                    "students_enrolled_this_month": 0,
                    "assessments_taken_this_month": 0,
                    "placements_this_month": 0,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Application data cleared. Administrator accounts and database tables were preserved."
            )
        )
