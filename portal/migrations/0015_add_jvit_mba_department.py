from django.db import migrations


def add_jvit_mba_department(apps, schema_editor):
    CollegeProfile = apps.get_model("portal", "CollegeProfile")
    Department = apps.get_model("portal", "Department")
    for college in CollegeProfile.objects.filter(college_name__icontains="JVIT"):
        Department.objects.get_or_create(
            college=college,
            code="MBA",
            defaults={"name": "MBA (Master of Business Administration)"},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0014_alter_collegeprofile_academic_year"),
    ]

    operations = [
        migrations.RunPython(add_jvit_mba_department, migrations.RunPython.noop),
    ]
