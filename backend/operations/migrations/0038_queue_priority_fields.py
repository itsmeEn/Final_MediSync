from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0037_restore_queue_messaging"),
    ]

    operations = [
        migrations.AddField(
            model_name="queuemanagement",
            name="is_priority",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="queuemanagement",
            name="priority_level",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="queuemanagement",
            name="priority_position",
            field=models.PositiveIntegerField(default=0),
        ),
    ]

