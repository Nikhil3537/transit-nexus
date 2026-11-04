from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0004_dailyattendance"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE dashboard_studentprofile ADD COLUMN IF NOT EXISTS phone varchar(30) NOT NULL DEFAULT '';",
                    reverse_sql="ALTER TABLE dashboard_studentprofile DROP COLUMN IF EXISTS phone;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="studentprofile",
                    name="phone",
                    field=models.CharField(blank=True, max_length=30),
                ),
            ],
        ),
    ]
