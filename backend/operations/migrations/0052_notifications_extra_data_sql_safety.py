from django.db import migrations


def ensure_notifications_extra_data_column(apps, schema_editor):
    table_name = "notifications"
    column_name = "extra_data"
    vendor = schema_editor.connection.vendor

    with schema_editor.connection.cursor() as cursor:
        if vendor == "postgresql":
            cursor.execute(
                "ALTER TABLE notifications "
                "ADD COLUMN IF NOT EXISTS extra_data jsonb NOT NULL DEFAULT '{}'::jsonb;"
            )
            return

        if vendor == "sqlite":
            cursor.execute("PRAGMA table_info(notifications);")
            cols = [row[1] for row in cursor.fetchall()]
            if column_name in cols:
                return
            cursor.execute("ALTER TABLE notifications ADD COLUMN extra_data TEXT;")
            return

        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} JSON;")
        except Exception:
            return


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0051_notification_extra_data"),
    ]

    operations = [
        migrations.RunPython(ensure_notifications_extra_data_column, migrations.RunPython.noop),
    ]

