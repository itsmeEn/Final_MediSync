from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from backend.users.models import User, PatientProfile
from rest_framework.test import APIClient


class PatientProfileNurseFormsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="patient@example.com",
            password="Testpass123",
            full_name="Test Patient",
            role=User.Role.PATIENT,
        )
        self.profile = PatientProfile.objects.create(user=self.user)

    def test_nursing_intake_and_validation(self):
        # Invalid pain_score
        intake = {
            "vitals": {"bp": "120/80", "hr": 72, "rr": 16, "temp_c": 36.8, "o2_sat": 98},
            "chief_complaint": "Headache",
            "pain_score": 12,
            "assessed_at": timezone.now().isoformat(),
        }
        self.profile.set_nursing_intake(intake)
        valid, errors = self.profile.validate_nurse_forms_minimal()
        self.assertFalse(valid)
        self.assertTrue(any("pain_score" in e for e in errors))

        # Valid pain_score
        intake["pain_score"] = 5
        self.profile.set_nursing_intake(intake)
        valid, errors = self.profile.validate_nurse_forms_minimal()
        self.assertTrue(valid)

    def test_flow_sheet_append(self):
        entry = {
            "time_of_reading": timezone.now().isoformat(),
            "repeated_vitals": {"bp": "118/76", "hr": 70, "rr": 15, "temp_c": 36.7, "o2_sat": 99, "pain": 2},
            "intake_ml": 250,
            "output_ml": 200,
            "site_checks": "IV site clean/dry/intact",
            "nursing_interventions": ["repositioned"],
        }
        self.profile.add_flow_sheet_entry(entry)
        self.profile.save()
        self.assertEqual(len(self.profile.graphic_flow_sheets), 1)

    def test_mar_validation(self):
        bad_entry = {
            "datetime_administered": timezone.now().isoformat(),
            "name": "Acetaminophen",
            "dose": "500 mg",
            "route": "PO",
            # missing nurse_initials
        }
        self.profile.add_mar_entry(bad_entry)
        valid, errors = self.profile.validate_nurse_forms_minimal()
        self.assertFalse(valid)
        self.assertTrue(any("nurse_initials" in e for e in errors))

        good_entry = dict(bad_entry)
        good_entry["nurse_initials"] = "AB"
        self.profile.medication_administration_records = []
        self.profile.add_mar_entry(good_entry)
        valid, errors = self.profile.validate_nurse_forms_minimal()
        self.assertTrue(valid)

    def test_education_entry(self):
        entry = {
            "topics": ["wound care", "new medication use"],
            "teaching_method": "verbal",
            "comprehension_level": "good",
            "return_demonstration": "successful",
            "barriers_to_learning": ["language"],
            "recorded_at": timezone.now().isoformat(),
        }
        self.profile.add_education_entry(entry)
        self.profile.save()
        self.assertEqual(len(self.profile.patient_education_record), 1)

    def test_discharge_summary_validation(self):
        ds = {
            "discharge_vitals": {"bp": "120/78", "hr": 72, "rr": 16, "temp_c": 36.8, "o2_sat": 98, "pain": 1},
            "understanding_confirmed": True,
            "written_instructions_provided": True,
            "follow_up_appointments_made": True,
            "equipment_needs": [],
            "transportation_status": "family",
            "nurse_signature": "Nurse A",
            "patient_acknowledgment": True,
            # missing discharged_at
        }
        self.profile.set_discharge_summary(ds)
        valid, errors = self.profile.validate_nurse_forms_minimal()
        self.assertFalse(valid)
        self.assertTrue(any("discharged_at" in e for e in errors))

        ds["discharged_at"] = timezone.now().isoformat()
        self.profile.set_discharge_summary(ds)
        valid, errors = self.profile.validate_nurse_forms_minimal()
        self.assertTrue(valid)


class PatientProfileDoctorFormsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="patient@example.com",
            password="Testpass123",
            full_name="Test Patient",
            role=User.Role.PATIENT,
        )
        self.profile = PatientProfile.objects.create(user=self.user)

    def test_history_physical_form_creation(self):
        hp_form = {
            "patient_name": "John Doe",
            "dob": "1985-05-15",
            "mrn": "MRN123456",
            "provider_signature": "Dr. Smith",
            "chief_complaint": "Chest pain",
            "history_present_illness": "Patient presents with acute onset chest pain...",
            "past_medical_history": ["Hypertension", "Diabetes"],
            "social_history": {"smoking": "Never", "alcohol": "Occasional", "occupation": "Teacher"},
            "review_of_systems": {
                "cardiovascular": "Positive for chest pain",
                "respiratory": "Negative for SOB",
                "gastrointestinal": "Negative"
            },
            "physical_exam": {
                "general": "Alert and oriented",
                "vitals": {"bp": "140/90", "hr": 88, "rr": 18, "temp": 98.6},
                "cardiovascular": "Regular rate and rhythm",
                "respiratory": "Clear to auscultation bilaterally"
            },
            "assessment": "Chest pain, rule out MI",
            "diagnoses": [{"code": "R06.02", "description": "Shortness of breath"}],
            "plan": ["EKG", "Chest X-ray", "Cardiac enzymes", "Aspirin 81mg daily"],
            "created_at": timezone.now().isoformat()
        }
        
        self.profile.add_hp_form(hp_form)
        self.profile.save()
        self.assertEqual(len(self.profile.history_physical_forms), 1)
        self.assertEqual(self.profile.history_physical_forms[0]["chief_complaint"], "Chest pain")

    def test_progress_note_creation(self):
        progress_note = {
            "date_time": timezone.now().isoformat(),
            "subjective": "Patient reports feeling better, chest pain resolved",
            "objective": {
                "vitals": {"bp": "130/80", "hr": 75, "rr": 16, "temp": 98.2},
                "physical_exam": "Heart rate regular, lungs clear",
                "lab_results": ["Troponin negative", "EKG normal sinus rhythm"]
            },
            "assessment": "Chest pain resolved, likely musculoskeletal",
            "plan": "Discharge home with follow-up in 1 week",
            "follow_up_date": "2024-02-01",
            "provider_signature": "Dr. Smith"
        }
        
        self.profile.add_progress_note(progress_note)
        self.profile.save()
        self.assertEqual(len(self.profile.progress_notes), 1)
        self.assertEqual(self.profile.progress_notes[0]["assessment"], "Chest pain resolved, likely musculoskeletal")

    def test_provider_order_creation(self):
        provider_order = {
            "ordering_provider": "Dr. Smith",
            "date_time_placed": timezone.now().isoformat(),
            "medication_orders": [
                {
                    "drug_name": "Lisinopril",
                    "dose": "10mg",
                    "route": "PO",
                    "frequency": "Daily"
                }
            ],
            "diagnostic_orders": [
                {
                    "test_name": "Complete Blood Count",
                    "priority": "Routine",
                    "reason": "Annual physical"
                }
            ],
            "consultation_orders": [
                {
                    "specialty": "Cardiology",
                    "question": "Evaluate chest pain"
                }
            ],
            "general_orders": {
                "diet": "Regular",
                "activity": "As tolerated"
            },
            "order_status": "New"
        }
        
        self.profile.add_provider_order(provider_order)
        self.profile.save()
        self.assertEqual(len(self.profile.provider_order_sheets), 1)
        self.assertEqual(len(self.profile.provider_order_sheets[0]["medication_orders"]), 1)

    def test_operative_report_creation(self):
        operative_report = {
            "patient_id": "MRN123456",
            "date_time_performed": timezone.now().isoformat(),
            "procedure_name": "Appendectomy",
            "indications": "Acute appendicitis",
            "consent_status": "Informed consent obtained",
            "anesthesia": {
                "type": "General",
                "dose": "Propofol 2mg/kg"
            },
            "procedure_steps": "1. Patient positioned supine...\n2. Abdomen prepped and draped...",
            "findings": "Inflamed appendix with perforation",
            "complications": "None",
            "disposition_plan": "Transfer to recovery room, NPO until bowel sounds return",
            "surgeon_signature": "Dr. Johnson"
        }
        
        self.profile.add_operative_report(operative_report)
        self.profile.save()
        self.assertEqual(len(self.profile.operative_procedure_reports), 1)
        self.assertEqual(self.profile.operative_procedure_reports[0]["procedure_name"], "Appendectomy")

    def test_doctor_forms_validation(self):
        # Test H&P form validation - missing required fields
        incomplete_hp = {
            "patient_name": "John Doe",
            # missing other required fields
        }
        self.profile.add_hp_form(incomplete_hp)
        valid, errors = self.profile.validate_doctor_forms_minimal()
        self.assertFalse(valid)
        self.assertTrue(any("provider_signature" in e for e in errors))

        # Test progress note validation - missing required fields
        incomplete_progress = {
            "subjective": "Patient feels better",
            # missing date_time and provider_signature
        }
        self.profile.add_progress_note(incomplete_progress)
        valid, errors = self.profile.validate_doctor_forms_minimal()
        self.assertFalse(valid)
        self.assertTrue(any("date_time" in e for e in errors))

        # Test provider order validation - missing required fields
        incomplete_order = {
            "medication_orders": [{"drug_name": "Aspirin"}],
            # missing ordering_provider and date_time_placed
        }
        self.profile.add_provider_order(incomplete_order)
        valid, errors = self.profile.validate_doctor_forms_minimal()
        self.assertFalse(valid)
        self.assertTrue(any("ordering_provider" in e for e in errors))

        # Test operative report validation - missing required fields
        incomplete_operative = {
            "procedure_name": "Surgery",
            # missing surgeon_signature and date_time_performed
        }
        self.profile.add_operative_report(incomplete_operative)
        valid, errors = self.profile.validate_doctor_forms_minimal()
        self.assertFalse(valid)
        self.assertTrue(any("surgeon_signature" in e for e in errors))

    def test_doctor_forms_context_methods(self):
        # Test that form context includes doctor-centric forms
        context = self.profile.get_form_fields_context()
        self.assertIn("history_physical", context["groups"])
        self.assertIn("progress_notes", context["groups"])
        self.assertIn("provider_orders", context["groups"])
        self.assertIn("operative_reports", context["groups"])

        # Test blank form context
        blank_context = self.profile.get_blank_form_fields_context()
        self.assertIn("history_physical", blank_context["groups"])
        self.assertIn("progress_notes", blank_context["groups"])
        self.assertIn("provider_orders", blank_context["groups"])
        self.assertIn("operative_reports", blank_context["groups"])

    def test_multiple_doctor_forms_entries(self):
        # Add multiple H&P forms
        for i in range(3):
            hp_form = {
                "patient_name": f"Patient {i}",
                "provider_signature": f"Dr. {i}",
                "chief_complaint": f"Complaint {i}",
                "created_at": timezone.now().isoformat()
            }
            self.profile.add_hp_form(hp_form)
        
        # Add multiple progress notes
        for i in range(2):
            progress_note = {
                "date_time": timezone.now().isoformat(),
                "subjective": f"Progress {i}",
                "provider_signature": f"Dr. {i}"
            }
            self.profile.add_progress_note(progress_note)
        
        self.profile.save()
        self.assertEqual(len(self.profile.history_physical_forms), 3)
        self.assertEqual(len(self.profile.progress_notes), 2)


class PsychiatricOpdDoctorEndpointsTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            email="psych-patient@example.com",
            password="Testpass123",
            full_name="Psych Patient",
            role=User.Role.PATIENT,
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="AdminPass123",
            full_name="Admin",
            role="admin",
            verification_status="approved",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_psychiatric_opd_requires_registration_then_allows(self):
        url = f"/users/doctor/patient/{self.patient_profile.id}/psychiatric-opd/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("registration", (resp.json() or {}).get("error", "").lower())

        self.patient_profile.nursing_intake_assessment = {"registration": {"mrn": "MRN-1"}}
        self.patient_profile.save(update_fields=["nursing_intake_assessment"])

        resp2 = self.client.get(url)
        self.assertEqual(resp2.status_code, 200)
        data = resp2.json() or {}
        self.assertTrue(data.get("success"))


class PatientReportedSymptomsPrefillTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            email="symptom-patient@example.com",
            password="Testpass123",
            full_name="Symptom Patient",
            role=User.Role.PATIENT,
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

        self.nurse_user = User.objects.create_user(
            email="nurse@example.com",
            password="Testpass123",
            full_name="Test Nurse",
            role=User.Role.NURSE,
            verification_status="approved",
        )

        self.patient_client = APIClient()
        self.patient_client.force_authenticate(user=self.patient_user)
        self.nurse_client = APIClient()
        self.nurse_client.force_authenticate(user=self.nurse_user)

    def test_patient_symptoms_prefill_available_to_nurse(self):
        resp = self.patient_client.post("/users/patient/symptoms/", {"symptoms": "Masakit ang ulo"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue((resp.json() or {}).get("success"))

        nurse_get = self.nurse_client.get(f"/users/nurse/patient/{self.patient_profile.id}/intake/")
        self.assertEqual(nurse_get.status_code, 200)
        payload = nurse_get.json() or {}
        self.assertTrue(payload.get("success"))
        data = payload.get("data") or {}
        prefill = (data.get("patient_reported_prefill") or {})
        self.assertTrue(prefill.get("is_relevant"))
        self.assertEqual(prefill.get("symptoms"), "Masakit ang ulo")

    def test_nurse_put_preserves_patient_reported_block(self):
        self.patient_profile.nursing_intake_assessment = {
            "patient_reported": {
                "symptoms": "Fever and cough",
                "submitted_at": timezone.now().isoformat(),
                "source": "patient_medical_history",
            }
        }
        self.patient_profile.save(update_fields=["nursing_intake_assessment"])

        put_resp = self.nurse_client.put(
            f"/users/nurse/patient/{self.patient_profile.id}/intake/",
            {"chief_complaint": "Fever and cough"},
            format="json",
        )
        self.assertEqual(put_resp.status_code, 200)

        nurse_get = self.nurse_client.get(f"/users/nurse/patient/{self.patient_profile.id}/intake/")
        self.assertEqual(nurse_get.status_code, 200)
        data = (nurse_get.json() or {}).get("data") or {}
        intake = data
        self.assertIn("patient_reported", intake)
        self.assertEqual((intake.get("patient_reported") or {}).get("symptoms"), "Fever and cough")

    def test_outdated_symptoms_not_used_for_prefill(self):
        old = (timezone.now() - timedelta(days=10)).isoformat()
        self.patient_profile.nursing_intake_assessment = {
            "patient_reported": {"symptoms": "Old symptom", "submitted_at": old, "source": "patient_medical_history"}
        }
        self.patient_profile.save(update_fields=["nursing_intake_assessment"])

        nurse_get = self.nurse_client.get(f"/users/nurse/patient/{self.patient_profile.id}/intake/")
        self.assertEqual(nurse_get.status_code, 200)
        data = (nurse_get.json() or {}).get("data") or {}
        prefill = data.get("patient_reported_prefill") or {}
        self.assertFalse(prefill.get("is_relevant"))
        self.assertEqual(prefill.get("symptoms"), "")

    def test_patient_pre_intake_route_supported(self):
        resp = self.patient_client.post(
            "/patient/pre-intake/",
            {"symptoms": "Masakit ang ulo", "medical_history": "No known chronic illness"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue((resp.json() or {}).get("success"))

        nurse_get = self.nurse_client.get(f"/users/nurse/patient/{self.patient_profile.id}/intake/")
        self.assertEqual(nurse_get.status_code, 200)
        prefill = ((nurse_get.json() or {}).get("data") or {}).get("patient_reported_prefill") or {}
        self.assertTrue(prefill.get("is_relevant"))
        self.assertEqual(prefill.get("symptoms"), "Masakit ang ulo")
