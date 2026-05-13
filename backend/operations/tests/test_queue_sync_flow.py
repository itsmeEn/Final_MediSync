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

    def test_patient_can_leave_queue(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        leave_resp = pclient.post("/operations/queue/leave/", {"department": "OPD"}, format="json")
        self.assertEqual(leave_resp.status_code, 200)
        self.assertTrue(leave_resp.json().get("success"))
        self.assertTrue(leave_resp.json().get("removed"))

        # Leaving again is idempotent
        leave_resp2 = pclient.post("/operations/queue/leave/", {"department": "OPD"}, format="json")
        self.assertEqual(leave_resp2.status_code, 200)
        self.assertTrue(leave_resp2.json().get("success"))
        self.assertFalse(leave_resp2.json().get("removed"))

    def test_patient_summary_falls_back_to_active_department(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        summary_resp = pclient.get("/operations/patient/dashboard/summary/?department=Pharmacy")
        self.assertEqual(summary_resp.status_code, 200)
        sdata = summary_resp.json()
        self.assertEqual(sdata.get("activeDepartment"), "OPD")
        self.assertEqual(sdata.get("department"), "OPD")
        self.assertNotEqual(sdata.get("myPosition", ""), "")

    def test_patient_cannot_join_multiple_departments(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        join_resp2 = pclient.post("/operations/queue/join/", {"department": "Pharmacy"}, format="json")
        self.assertEqual(join_resp2.status_code, 409)
        data = join_resp2.json()
        self.assertEqual(data.get("department"), "OPD")

    def test_patient_summary_includes_position_in_queue(self):
        patient2 = User.objects.create_user(
            email="patient2.sync@example.com",
            password="StrongPass123",
            full_name="Patient Two",
            role=User.Role.PATIENT,
        )
        PatientProfile.objects.create(user=patient2, blood_type="O+", medical_condition="None")

        pclient1 = APIClient()
        pclient1.force_authenticate(self.patient)
        join_resp1 = pclient1.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp1.status_code, 201)

        pclient2 = APIClient()
        pclient2.force_authenticate(patient2)
        join_resp2 = pclient2.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp2.status_code, 201)

        summary_resp = pclient2.get("/operations/patient/dashboard/summary/?department=OPD")
        self.assertEqual(summary_resp.status_code, 200)
        sdata = summary_resp.json()
        self.assertEqual(sdata.get("myQueueStatus"), "waiting")
        self.assertEqual(sdata.get("myPositionInQueue"), 2)
        self.assertTrue(isinstance(sdata.get("myQueueNumber"), int))

    def test_wait_estimate_runs_even_when_no_one_called_yet(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201, join_resp.content)

        summary_resp = pclient.get("/operations/patient/dashboard/summary/?department=OPD")
        self.assertEqual(summary_resp.status_code, 200, summary_resp.content)
        sdata = summary_resp.json()
        self.assertEqual(sdata.get("myQueueStatus"), "waiting")
        est_seconds = sdata.get("estimatedWaitSeconds")
        self.assertTrue(isinstance(est_seconds, int))
        self.assertGreater(est_seconds, 0)
