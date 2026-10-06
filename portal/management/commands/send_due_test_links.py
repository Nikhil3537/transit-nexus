from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mass_mail
from django.conf import settings
from django.utils import timezone

from dashboard.models import StudentProfile
from portal.models import OnlineTest


class Command(BaseCommand):
    help = "Email external assessment links when their scheduled opening time arrives."

    def handle(self, *args, **options):
        if "console.EmailBackend" in settings.EMAIL_BACKEND:
            raise CommandError(
                "Configure SMTP first. The console email backend does not deliver messages or mark test links as sent."
            )
        if not settings.EMAIL_HOST_PASSWORD:
            raise CommandError("Set EMAIL_HOST_PASSWORD in the .env file beside manage.py before sending test-link emails.")
        now = timezone.now()
        due_tests = OnlineTest.objects.filter(
            external_url__gt="",
            external_link_email_sent=False,
            opens_at__lte=now,
            closes_at__gt=now,
        ).select_related("college", "trainer__user")
        sent_tests = 0
        for test in due_tests:
            student_emails = StudentProfile.objects.filter(
                college_id=test.college_id,
                user__is_active=True,
            ).exclude(user__email="").values_list("user__email", flat=True)
            recipients = list(dict.fromkeys(
                [email.strip() for email in student_emails if email and email.strip()]
                + ([test.trainer.user.email.strip()] if test.trainer.user.is_active and test.trainer.user.email.strip() else [])
            ))
            if not recipients:
                self.stderr.write(f"No email recipients for test {test.pk} ({test.title}); will retry.")
                continue
            subject = f"Test is open: {test.title}"
            body = (
                f"{test.title} is now open.\n\n"
                f"Open the test here: {test.external_url}\n\n"
                f"Scheduled closing time: {timezone.localtime(test.closes_at).strftime('%d %b %Y, %I:%M %p')}"
            )
            messages = tuple((subject, body, None, [address]) for address in recipients)
            try:
                count = send_mass_mail(messages, fail_silently=False)
            except Exception as exc:
                self.stderr.write(f"Email failed for test {test.pk}: {exc}")
                continue
            test.external_link_email_sent = True
            test.save(update_fields=["external_link_email_sent"])
            sent_tests += 1
            self.stdout.write(f"Sent test {test.pk} link to {count} recipient(s).")
        self.stdout.write(f"Processed {sent_tests} test(s).")
