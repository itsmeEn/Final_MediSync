from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0049_queue_no_show"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    code=lambda apps, schema_editor: _add_department_column(schema_editor),
                    reverse_code=lambda apps, schema_editor: _drop_department_column(schema_editor),
                )
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


def _add_department_column(schema_editor):
    vendor = getattr(schema_editor.connection, "vendor", "")
    table = "appointment_management"
    col = "department"
    with schema_editor.connection.cursor() as cursor:
        if vendor == "sqlite":
            cursor.execute(f'PRAGMA table_info("{table}")')
            rows = cursor.fetchall() or []
            for r in rows:
                if len(r) >= 2 and r[1] == col:
                    return
            cursor.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{col}" VARCHAR(100) NOT NULL DEFAULT \'OPD\';'
            )
            return
        cursor.execute(
            "ALTER TABLE appointment_management "
            "ADD COLUMN IF NOT EXISTS department VARCHAR(100) NOT NULL DEFAULT 'OPD';"
        )


def _drop_department_column(schema_editor):
    vendor = getattr(schema_editor.connection, "vendor", "")
    if vendor == "sqlite":
        return
    schema_editor.execute("ALTER TABLE appointment_management DROP COLUMN IF EXISTS department;")
