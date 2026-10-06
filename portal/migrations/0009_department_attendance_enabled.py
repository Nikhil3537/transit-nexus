from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0008_trainerprofile_domain_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="attendance_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
