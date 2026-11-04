from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0004_studentprofile_phone"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'dashboard_dailyattendance' AND column_name = 'session_name'
                            ) AND NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'dashboard_dailyattendance' AND column_name = 'session_label'
                            ) THEN
                                ALTER TABLE dashboard_dailyattendance RENAME COLUMN session_name TO session_label;
                            ELSIF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'dashboard_dailyattendance' AND column_name = 'session_label'
                            ) THEN
                                ALTER TABLE dashboard_dailyattendance ADD COLUMN session_label varchar(120) NOT NULL DEFAULT 'Regular Session';
                            END IF;
                            ALTER TABLE dashboard_dailyattendance DROP CONSTRAINT IF EXISTS unique_student_session_attendance;
                            ALTER TABLE dashboard_dailyattendance DROP CONSTRAINT IF EXISTS unique_student_daily_attendance;
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint WHERE conname = 'unique_student_daily_attendance_session'
                            ) THEN
                                ALTER TABLE dashboard_dailyattendance ADD CONSTRAINT unique_student_daily_attendance_session UNIQUE (student_id, date, session_label);
                            END IF;
                        END $$;
                    """,
                    reverse_sql="""
                        ALTER TABLE dashboard_dailyattendance DROP CONSTRAINT IF EXISTS unique_student_daily_attendance_session;
                        ALTER TABLE dashboard_dailyattendance RENAME COLUMN session_label TO session_name;
                        ALTER TABLE dashboard_dailyattendance ADD CONSTRAINT unique_student_session_attendance UNIQUE (student_id, date, session_name);
                    """,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="dailyattendance",
                    name="session_label",
                    field=models.CharField(default="Regular Session", max_length=120),
                ),
                migrations.RemoveConstraint(
                    model_name="dailyattendance",
                    name="unique_student_daily_attendance",
                ),
                migrations.AddConstraint(
                    model_name="dailyattendance",
                    constraint=models.UniqueConstraint(
                        fields=("student", "date", "session_label"),
                        name="unique_student_daily_attendance_session",
                    ),
                ),
            ],
        ),
    ]
