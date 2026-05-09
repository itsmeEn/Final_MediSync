from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0049_queue_no_show"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE appointment_management "
                        "ADD COLUMN IF NOT EXISTS department VARCHAR(100) NOT NULL DEFAULT 'OPD';"
                    ),
                    reverse_sql=(
                        "ALTER TABLE appointment_management "
                        "DROP COLUMN IF EXISTS department;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="appointmentmanagement",
                    name="department",
                    field=models.CharField(default="OPD", help_text="Department for the appointment.", max_length=100),
                ),
            ],
        ),
    ]

