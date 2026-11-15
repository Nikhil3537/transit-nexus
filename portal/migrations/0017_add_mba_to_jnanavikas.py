from django.db import migrations


def add_mba_to_jnanavikas(apps, schema_editor):
    CollegeProfile = apps.get_model("portal", "CollegeProfile")
    Department = apps.get_model("portal", "Department")
    for college in CollegeProfile.objects.filter(college_name__icontains="Jnanavikas"):
        Department.objects.update_or_create(
            college=college,
            code="MBA",
            defaults={"name": "MBA (Master of Business Administration)"},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0016_normalize_jvit_mba_department"),
    ]

    operations = [
        migrations.RunPython(add_mba_to_jnanavikas, migrations.RunPython.noop),
    ]
