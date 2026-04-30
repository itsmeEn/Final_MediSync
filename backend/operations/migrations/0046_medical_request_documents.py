from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("operations", "0045_patientassignmentauditlog_formaccesslog"),
    ]

    operations = [
        migrations.CreateModel(
            name="MedicalRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_medical_certificate", models.BooleanField(default=False)),
                ("request_prescription", models.BooleanField(default=False)),
                ("patient_message", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("fulfilled", "Fulfilled"), ("cancelled", "Cancelled")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("doctor_message", models.TextField(blank=True, default="")),
                ("fulfilled_at", models.DateTimeField(blank=True, null=True)),
                ("certificate_details", models.JSONField(blank=True, default=dict)),
                ("prescription_details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="medical_requests",
                        to="operations.patientassignment",
                    ),
                ),
                (
                    "consultation_notes",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="medical_requests",
                        to="operations.consultationnotes",
                    ),
                ),
                (
                    "doctor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="medical_requests",
                        to="users.generaldoctorprofile",
                    ),
                ),
                (
                    "fulfilled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="medical_requests_fulfilled",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="medical_requests",
                        to="users.patientprofile",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="medical_requests_requested",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "medical_requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="GeneratedMedicalDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "doc_type",
                    models.CharField(
                        choices=[("medical_certificate", "Medical Certificate"), ("prescription", "Prescription")],
                        max_length=32,
                    ),
                ),
                ("document_number", models.CharField(db_index=True, max_length=64)),
                ("file", models.FileField(upload_to="medical_documents/%Y/%m/")),
                ("sha256_hex", models.CharField(blank=True, default="", max_length=64)),
                ("signature_hmac_hex", models.CharField(blank=True, default="", max_length=128)),
                ("encrypted_password", models.TextField(blank=True, default="")),
                ("is_encrypted", models.BooleanField(default=True)),
                (
                    "email_delivery_status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("email_sent_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("authenticated_at", models.DateTimeField()),
                ("ip_address", models.CharField(blank=True, default="", max_length=64)),
                ("user_agent", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generated_medical_documents",
                        to="operations.patientassignment",
                    ),
                ),
                (
                    "consultation_notes",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generated_medical_documents",
                        to="operations.consultationnotes",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generated_medical_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "doctor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="generated_medical_documents",
                        to="users.generaldoctorprofile",
                    ),
                ),
                (
                    "medical_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="operations.medicalrequest",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="generated_medical_documents",
                        to="users.patientprofile",
                    ),
                ),
            ],
            options={
                "db_table": "generated_medical_documents",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="medicalrequest",
            index=models.Index(fields=["patient", "created_at"], name="medical_req_patient_created_idx"),
        ),
        migrations.AddIndex(
            model_name="medicalrequest",
            index=models.Index(fields=["status", "created_at"], name="medical_req_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="generatedmedicaldocument",
            index=models.Index(fields=["doc_type", "created_at"], name="gendoc_type_created_idx"),
        ),
        migrations.AddIndex(
            model_name="generatedmedicaldocument",
            index=models.Index(fields=["patient", "created_at"], name="gendoc_patient_created_idx"),
        ),
        migrations.AddIndex(
            model_name="generatedmedicaldocument",
            index=models.Index(fields=["doctor", "created_at"], name="gendoc_doctor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="generatedmedicaldocument",
            index=models.Index(fields=["document_number"], name="gendoc_docnum_idx"),
        ),
    ]
