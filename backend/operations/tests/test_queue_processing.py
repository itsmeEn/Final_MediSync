from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch
from datetime import timedelta

from backend.users.models import User, NurseProfile, PatientProfile
from backend.operations.models import QueueStatus, QueueManagement, Notification


class QueueProcessingTests(TestCase):
    def setUp(self):
        # Create users
        self.nurse_user = User.objects.create_user(
            email="nurse@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Joy",
        )
        self.patient_user = User.objects.create_user(
            email="patient@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="John Patient",
        )

        # Profiles
        self.nurse_profile = NurseProfile.objects.create(
            user=self.nurse_user, department="OPD"
        )
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user
        )

        # Queue status (open)
        self.queue_status = QueueStatus.objects.create(
            department="OPD",
            is_open=True,
        )

        # Create a waiting queue entry using bulk_create to avoid model save overrides
        QueueManagement.objects.bulk_create([
            QueueManagement(
                patient=self.patient_profile,
                queue_number=1,
                department="OPD",
                status="waiting",
                position_in_queue=1,
                enqueue_time=timezone.now(),
            )
        ])

        self.client = APIClient()

    def test_start_queue_processing_updates_status_and_sends_notification(self):
        # Stub channel layer to avoid external Redis dependency
        class DummyChannelLayer:
            async def group_send(self, group, event):
                return None

        self.client.force_authenticate(user=self.nurse_user)
        with patch("backend.operations.views.get_channel_layer", return_value=DummyChannelLayer()):
            resp = self.client.post(
                "/operations/queue/start-processing/",
                {"department": "OPD"},
                format="json",
            )

        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        # Queue status should reflect current serving and zero waiting
        self.assertIn("queue_status", data)
        self.assertEqual(data["queue_status"].get("current_serving"), 1)
        self.assertEqual(data["queue_status"].get("total_waiting"), 0)

        # Queue entry should be marked as called
        entry = QueueManagement.objects.get(queue_number=1)
        self.assertEqual(entry.status, "called")

        self.assertIn("notification_results", data)

    def test_confirm_notification_delivery_updates_fields(self):
        # Create a pending notification for patient
        notif = Notification.objects.create(
            user=self.patient_user,
            message="Test delivery",
            channel=Notification.CHANNEL_WEBSOCKET,
            delivery_status=Notification.DELIVERY_PENDING,
        )

        # Patient confirms delivery
        self.client.force_authenticate(user=self.patient_user)
        resp = self.client.post(
            "/operations/queue/notifications/confirm/",
            {"notification_id": notif.id},
            format="json",
        )

        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertIn("notification", data)
        updated = data["notification"]
        self.assertEqual(updated.get("delivery_status"), Notification.DELIVERY_DELIVERED)
        self.assertIsNotNone(updated.get("delivered_at"))

    def test_patient_dashboard_summary_estimated_wait_accounts_for_active_elapsed_time(self):
        now = timezone.now()
        QueueManagement.objects.filter(queue_number=1).update(status="called", called_at=now - timedelta(minutes=10))

        other_user = User.objects.create_user(
            email="patient2@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Jane Patient",
        )
        other_profile = PatientProfile.objects.create(user=other_user)
        QueueManagement.objects.create(
            patient=other_profile,
            queue_number=2,
            department="OPD",
            status="waiting",
            position_in_queue=2,
            enqueue_time=now,
        )

        self.client.force_authenticate(user=other_user)
        resp = self.client.get("/operations/patient/dashboard/summary/", {"department": "OPD"})
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data.get("myPosition"), "2")
        self.assertEqual(data.get("estimatedWaitMins"), 5)
        secs = int(data.get("estimatedWaitSeconds") or 0)
        self.assertTrue(250 <= secs <= 300, secs)
