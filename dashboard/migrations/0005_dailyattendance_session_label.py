from django.db import migrations, models


POSTGRES_FORWARD_SQL = """
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
"""

POSTGRES_REVERSE_SQL = """
    ALTER TABLE dashboard_dailyattendance DROP CONSTRAINT IF EXISTS unique_student_daily_attendance_session;
    ALTER TABLE dashboard_dailyattendance RENAME COLUMN session_label TO session_name;
    ALTER TABLE dashboard_dailyattendance ADD CONSTRAINT unique_student_session_attendance UNIQUE (student_id, date, session_name);
"""


def migrate_attendance_session_label(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        schema_editor.execute(POSTGRES_FORWARD_SQL)
        return
    if connection.vendor != "sqlite":
        raise RuntimeError(f"Unsupported database for attendance migration: {connection.vendor}")

    model = apps.get_model("dashboard", "DailyAttendance")
    table = model._meta.db_table
    quoted_table = schema_editor.quote_name(table)
    with connection.cursor() as cursor:
        columns = {
            item.name for item in connection.introspection.get_table_description(cursor, table)
        }
        constraints = connection.introspection.get_constraints(cursor, table)

    if "session_label" not in columns:
        if "session_name" in columns:
            schema_editor.execute(
                f"ALTER TABLE {quoted_table} RENAME COLUMN "
                f"{schema_editor.quote_name('session_name')} TO {schema_editor.quote_name('session_label')};"
            )
        else:
            schema_editor.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN "
                f"{schema_editor.quote_name('session_label')} varchar(120) NOT NULL DEFAULT 'Regular Session';"
            )

    for constraint_name in ("unique_student_session_attendance", "unique_student_daily_attendance"):
        if constraint_name in constraints and constraints[constraint_name].get("index"):
            schema_editor.execute(f"DROP INDEX IF EXISTS {schema_editor.quote_name(constraint_name)};")

    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, table)
    new_constraint = "unique_student_daily_attendance_session"
    if new_constraint not in constraints:
        schema_editor.execute(
            f"CREATE UNIQUE INDEX {schema_editor.quote_name(new_constraint)} ON {quoted_table} "
            f"({schema_editor.quote_name('student_id')}, {schema_editor.quote_name('date')}, "
            f"{schema_editor.quote_name('session_label')});"
        )


def reverse_attendance_session_label(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        schema_editor.execute(POSTGRES_REVERSE_SQL)
        return
    if connection.vendor != "sqlite":
        raise RuntimeError(f"Unsupported database for attendance migration: {connection.vendor}")

    model = apps.get_model("dashboard", "DailyAttendance")
    table = model._meta.db_table
    quoted_table = schema_editor.quote_name(table)
    schema_editor.execute(
        f"DROP INDEX IF EXISTS {schema_editor.quote_name('unique_student_daily_attendance_session')};"
    )
    with connection.cursor() as cursor:
        columns = {
            item.name for item in connection.introspection.get_table_description(cursor, table)
        }
    if "session_label" in columns and "session_name" not in columns:
        schema_editor.execute(
            f"ALTER TABLE {quoted_table} RENAME COLUMN "
            f"{schema_editor.quote_name('session_label')} TO {schema_editor.quote_name('session_name')};"
        )
    schema_editor.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {schema_editor.quote_name('unique_student_session_attendance')} "
        f"ON {quoted_table} ({schema_editor.quote_name('student_id')}, {schema_editor.quote_name('date')}, "
        f"{schema_editor.quote_name('session_name')});"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0004_studentprofile_phone"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(migrate_attendance_session_label, reverse_attendance_session_label),
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
