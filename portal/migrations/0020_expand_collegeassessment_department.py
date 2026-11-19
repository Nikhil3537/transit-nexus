from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0019_set_2025_27_to_odd_semester"),
    ]

    operations = [
        migrations.AlterField(
            model_name="collegeassessment",
            name="department",
            field=models.CharField(max_length=150),
        ),
    ]
