from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from backend.users.models import User, PatientProfile


class QueueSyncFlowTests(TestCase):
    def setUp(self):
        # Create a nurse for reading queue
        self.nurse = User.objects.create_user(
            email="nurse.sync@example.com",
            password="StrongPass123",
            full_name="Nurse Sync",
            role=User.Role.NURSE,
        )
        # Create a patient to join queue
        self.patient = User.objects.create_user(
            email="patient.sync@example.com",
            password="StrongPass123",
            full_name="Patient Sync",
            role=User.Role.PATIENT,
        )
        PatientProfile.objects.create(user=self.patient, blood_type="O+", medical_condition="None")

    def test_patient_join_updates_nurse_feed_and_patient_summary(self):
        # Patient joins queue
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        # Nurse sees queue
        nclient = APIClient()
        nclient.force_authenticate(self.nurse)
        nurse_resp = nclient.get("/operations/nurse/queue/patients/?department=OPD")
        self.assertEqual(nurse_resp.status_code, 200)
        data = nurse_resp.json()
        self.assertTrue(len(data.get("normal_queue", [])) >= 1)
        self.assertTrue(len(data.get("all_patients", [])) >= 1)

        # Patient summary reflects position
        summary_resp = pclient.get("/operations/patient/dashboard/summary/?department=OPD")
        self.assertEqual(summary_resp.status_code, 200)
        sdata = summary_resp.json()
        self.assertTrue(isinstance(sdata.get("myPosition", ""), str))
        # myPosition can be 'Now Serving' or a queue number string, but should not be empty
        self.assertNotEqual(sdata.get("myPosition", ""), "")

    def test_priority_join_appears_in_priority_queue(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD", "priority_level": "pwd"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        nclient = APIClient()
        nclient.force_authenticate(self.nurse)
        nurse_resp = nclient.get("/operations/nurse/queue/patients/?department=OPD")
        self.assertEqual(nurse_resp.status_code, 200)
        data = nurse_resp.json()
        self.assertTrue(len(data.get("priority_queue", [])) >= 1)
