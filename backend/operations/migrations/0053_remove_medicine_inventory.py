from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0053_merge_20260510_0144"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "DROP TABLE IF EXISTS medicine_inventory;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.DeleteModel(
                    name="MedicineInventory",
                ),
            ],
        ),
    ]
