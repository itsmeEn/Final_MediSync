from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0039_queuestatus_last_updated_by"),
        ("users", "0015_remove_patientprofile_hospital_fk"),
    ]

    operations = [
        migrations.CreateModel(
            name="PsychiatricOpdQuestionnaire",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("draft", "draft"), ("submitted", "submitted")], default="draft", max_length=16)),
                ("encrypted_payload", models.TextField()),
                ("payload_sha256", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_psychiatric_opd_questionnaires", to=settings.AUTH_USER_MODEL)),
                ("patient_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="psychiatric_opd_questionnaires", to="users.patientprofile")),
            ],
            options={
                "db_table": "psychiatric_opd_questionnaires",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="psychiatricopdquestionnaire",
            index=models.Index(fields=["patient_profile", "status"], name="psychiatric_patient__f7fddb_idx"),
        ),
        migrations.AddIndex(
            model_name="psychiatricopdquestionnaire",
            index=models.Index(fields=["updated_at"], name="psychiatric_updated__8d36ea_idx"),
        ),
    ]
