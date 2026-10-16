from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0011_alter_adminstudentrecord_department"),
    ]

    operations = [
        migrations.AlterField(
            model_name="onlinetest",
            name="trainer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="online_tests",
                to="portal.trainerprofile",
            ),
        ),
    ]
