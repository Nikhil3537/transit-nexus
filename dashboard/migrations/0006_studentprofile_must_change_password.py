from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0005_dailyattendance_session_label")]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="must_change_password",
            field=models.BooleanField(
                default=False,
                help_text="Require the student to choose a new password at first sign-in.",
            ),
        ),
    ]
