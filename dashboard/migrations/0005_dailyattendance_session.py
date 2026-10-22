from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0004_dailyattendance"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyattendance",
            name="session_name",
            field=models.CharField(default="General Session", max_length=150),
        ),
        migrations.RemoveConstraint(
            model_name="dailyattendance",
            name="unique_student_daily_attendance",
        ),
        migrations.AddConstraint(
            model_name="dailyattendance",
            constraint=models.UniqueConstraint(
                fields=("student", "date", "session_name"),
                name="unique_student_session_attendance",
            ),
        ),
    ]
