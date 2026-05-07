from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_site", "0006_hospital_logo"),
    ]

    operations = [
        migrations.AddField(
            model_name="adminuser",
            name="password_reset_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="adminuser",
            name="password_reset_token",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

