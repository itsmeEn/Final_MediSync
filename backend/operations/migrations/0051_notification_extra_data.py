from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0050_appointment_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="extra_data",
            field=models.JSONField(blank=True, default=dict, help_text="Extra metadata for the notification (e.g. transfer_id)."),
        ),
    ]

