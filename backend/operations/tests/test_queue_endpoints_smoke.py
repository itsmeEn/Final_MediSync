from django.test import TestCase
from rest_framework.test import APIClient
from backend.users.models import User
from django.utils import timezone
from backend.operations.models import DailySequenceCounter


class QueueEndpointsSmokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="nurse@example.com",
            password="StrongPass123",
            full_name="Nurse User",
            role=User.Role.NURSE,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_nurse_queue_patients_shape(self):
        resp = self.client.get("/operations/nurse/queue/patients/?department=OPD")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("normal_queue", data)
        self.assertIn("priority_queue", data)
        self.assertIsInstance(data["normal_queue"], list)
        self.assertIsInstance(data["priority_queue"], list)

    def test_create_and_list_queue_schedule(self):
        create_payload = {
            "department": "OPD",
            "start_time": "08:00",
            "end_time": "17:00",
            "days_of_week": [0, 1, 2, 3, 4],
            "is_active": True,
        }
        create_resp = self.client.post("/operations/queue/schedules/", create_payload, format="json")
        self.assertEqual(create_resp.status_code, 201)
        created = create_resp.json()
        self.assertEqual(created["department"], "OPD")
        list_resp = self.client.get("/operations/queue/schedules/")
        self.assertEqual(list_resp.status_code, 200)
        items = list_resp.json()
        self.assertTrue(any(item["id"] == created["id"] for item in items))

    def test_toggle_queue_status(self):
        payload = {"department": "OPD", "is_open": True}
        resp = self.client.post("/operations/queue/status/", payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("is_open"))
        get_resp = self.client.get("/operations/queue/status/?department=OPD")
        self.assertEqual(get_resp.status_code, 200)
        self.assertTrue(get_resp.json().get("is_open"))

    def test_daily_reset_resets_daily_counter(self):
        today = timezone.now().date()
        DailySequenceCounter.objects.create(department="OPD", date=today, current_value=7)
        resp = self.client.post("/operations/queue/daily-reset/", {"department": "OPD"}, format="json")
        self.assertEqual(resp.status_code, 200)
        counter = DailySequenceCounter.objects.get(department="OPD", date=today)
        self.assertEqual(counter.current_value, 0)
