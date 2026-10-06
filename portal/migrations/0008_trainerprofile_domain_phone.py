from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0007_onlinetest_external_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="trainerprofile",
            name="domain",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="trainerprofile",
            name="phone",
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
