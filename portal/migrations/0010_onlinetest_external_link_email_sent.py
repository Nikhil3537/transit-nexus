from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0009_department_attendance_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="onlinetest",
            name="external_link_email_sent",
            field=models.BooleanField(default=False),
        ),
    ]
