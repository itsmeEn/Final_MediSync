from django.db import migrations, models

import secrets
import string


def _generate_patient_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "PAT-" + "".join(secrets.choice(alphabet) for _ in range(8))


def populate_patient_ids(apps, schema_editor):
    PatientProfile = apps.get_model("users", "PatientProfile")
    existing = set(
        PatientProfile.objects.exclude(patient_id__isnull=True)
        .exclude(patient_id="")
        .values_list("patient_id", flat=True)
    )

    for profile in PatientProfile.objects.filter(models.Q(patient_id__isnull=True) | models.Q(patient_id="")):
        candidate = _generate_patient_id()
        while candidate in existing or PatientProfile.objects.filter(patient_id=candidate).exists():
            candidate = _generate_patient_id()
        profile.patient_id = candidate
        profile.save(update_fields=["patient_id"])
        existing.add(candidate)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0015_remove_patientprofile_hospital_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientprofile",
            name="patient_id",
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=20, null=True, unique=True),
        ),
        migrations.RunPython(populate_patient_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="patientprofile",
            name="patient_id",
            field=models.CharField(db_index=True, editable=False, max_length=20, unique=True),
        ),
    ]

