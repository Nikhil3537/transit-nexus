from django.db import migrations


def set_2025_27_colleges_to_odd_semester(apps, schema_editor):
    CollegeProfile = apps.get_model("portal", "CollegeProfile")
    CollegeProfile.objects.filter(
        academic_year="2025-27",
        semester_label="Even Semester",
    ).update(semester_label="Odd Semester")


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0018_trainingfeedback"),
    ]

    operations = [
        migrations.RunPython(set_2025_27_colleges_to_odd_semester, migrations.RunPython.noop),
    ]
