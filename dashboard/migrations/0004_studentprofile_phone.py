from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0004_dailyattendance"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="phone",
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
