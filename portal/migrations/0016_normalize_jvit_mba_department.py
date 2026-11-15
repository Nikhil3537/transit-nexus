from django.db import migrations


def normalize_jvit_mba_department(apps, schema_editor):
    CollegeProfile = apps.get_model("portal", "CollegeProfile")
    Department = apps.get_model("portal", "Department")
    for college in CollegeProfile.objects.filter(college_name__icontains="JVIT"):
        Department.objects.filter(college=college, code="MBA").update(
            name="MBA (Master of Business Administration)"
        )
        Department.objects.filter(
            college=college, name__iexact="MBA"
        ).update(
            code="MBA",
            name="MBA (Master of Business Administration)",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0015_add_jvit_mba_department"),
    ]

    operations = [
        migrations.RunPython(normalize_jvit_mba_department, migrations.RunPython.noop),
    ]
