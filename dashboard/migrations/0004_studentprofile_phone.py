from django.db import migrations, models


def add_phone_if_missing(apps, schema_editor):
    model = apps.get_model("dashboard", "StudentProfile")
    table = model._meta.db_table
    column = "phone"
    with schema_editor.connection.cursor() as cursor:
        columns = {
            item.name
            for item in schema_editor.connection.introspection.get_table_description(cursor, table)
        }
    if column not in columns:
        schema_editor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table)} "
            f"ADD COLUMN {schema_editor.quote_name(column)} varchar(30) NOT NULL DEFAULT '';"
        )


def remove_phone_if_present(apps, schema_editor):
    model = apps.get_model("dashboard", "StudentProfile")
    table = model._meta.db_table
    column = "phone"
    with schema_editor.connection.cursor() as cursor:
        columns = {
            item.name
            for item in schema_editor.connection.introspection.get_table_description(cursor, table)
        }
    if column in columns:
        schema_editor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table)} "
            f"DROP COLUMN {schema_editor.quote_name(column)};"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0004_dailyattendance"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_phone_if_missing, remove_phone_if_present),
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
