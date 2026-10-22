from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0003_studentprofile_department"),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyAttendance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("is_present", models.BooleanField(default=True)),
                ("marked_at", models.DateTimeField(auto_now_add=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="daily_attendance", to="dashboard.studentprofile")),
            ],
            options={"ordering": ["-date"]},
        ),
        migrations.AddConstraint(
            model_name="dailyattendance",
            constraint=models.UniqueConstraint(fields=("student", "date"), name="unique_student_daily_attendance"),
        ),
    ]
