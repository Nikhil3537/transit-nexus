from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0012_alter_onlinetest_trainer_nullable")]

    operations = [
        migrations.AddField(model_name="collegeprofile", name="account_role", field=models.CharField(choices=[("college_admin", "College Admin"), ("principal", "Principal"), ("placement", "Placement Department"), ("hod", "Head of Department")], default="college_admin", max_length=20)),
        migrations.AddField(model_name="collegeprofile", name="department_scope", field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name="collegeprofile", name="workspace", field=models.ForeignKey(blank=True, help_text="The shared college workspace for this account.", null=True, on_delete=models.CASCADE, related_name="role_accounts", to="portal.collegeprofile")),
    ]
