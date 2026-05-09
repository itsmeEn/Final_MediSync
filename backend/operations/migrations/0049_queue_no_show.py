from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0048_medical_record_transfers"),
    ]

    operations = [
        migrations.AddField(
            model_name="queuemanagement",
            name="called_at",
            field=models.DateTimeField(blank=True, help_text="Timestamp when the patient was called.", null=True),
        ),
        migrations.AddField(
            model_name="queuemanagement",
            name="checked_in_at",
            field=models.DateTimeField(blank=True, help_text="Timestamp when the patient confirmed arrival after being called.", null=True),
        ),
        migrations.AddField(
            model_name="queuemanagement",
            name="grace_expires_at",
            field=models.DateTimeField(blank=True, help_text="Timestamp when the no-show grace period expires.", null=True),
        ),
        migrations.AddField(
            model_name="queuemanagement",
            name="last_no_show_at",
            field=models.DateTimeField(blank=True, help_text="Timestamp of the most recent no-show event for this queue entry.", null=True),
        ),
        migrations.AddField(
            model_name="queuemanagement",
            name="no_show_action",
            field=models.CharField(blank=True, default="", help_text="Policy action taken for the last no-show event (move_to_end/remove).", max_length=32),
        ),
        migrations.CreateModel(
            name="QueueNoShowAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("department", models.CharField(blank=True, default="", max_length=100)),
                ("event", models.CharField(choices=[("called", "called"), ("checked_in", "checked_in"), ("no_show_marked", "no_show_marked"), ("no_show_moved_to_end", "no_show_moved_to_end"), ("no_show_removed", "no_show_removed"), ("late_arrival", "late_arrival"), ("notification_sent", "notification_sent"), ("notification_failed", "notification_failed"), ("system_error", "system_error")], max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="no_show_audit_logs", to=settings.AUTH_USER_MODEL)),
                ("patient", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="no_show_audit_logs", to="users.patientprofile")),
                ("queue_entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="no_show_audit_logs", to="operations.queuemanagement")),
            ],
            options={
                "db_table": "queue_no_show_audit_logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="queuenoshowauditlog",
            index=models.Index(fields=["created_at"], name="queue_no_sh_created_4ee7d9_idx"),
        ),
        migrations.AddIndex(
            model_name="queuenoshowauditlog",
            index=models.Index(fields=["department", "created_at"], name="queue_no_sh_departm_619cdc_idx"),
        ),
        migrations.AddIndex(
            model_name="queuenoshowauditlog",
            index=models.Index(fields=["event", "created_at"], name="queue_no_sh_event_7e42fe_idx"),
        ),
        migrations.AddIndex(
            model_name="queuenoshowauditlog",
            index=models.Index(fields=["patient", "created_at"], name="queue_no_sh_patient_8bd07e_idx"),
        ),
        migrations.AddIndex(
            model_name="queuenoshowauditlog",
            index=models.Index(fields=["queue_entry", "created_at"], name="queue_no_sh_queue_e_9e1c5c_idx"),
        ),
    ]

