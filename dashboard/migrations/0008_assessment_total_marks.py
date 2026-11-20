from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0007_alter_dailyattendance_options_and_more")]

    operations = [
        migrations.AddField(
            model_name="assessment",
            name="total_marks",
            field=models.PositiveIntegerField(default=100),
        ),
    ]
