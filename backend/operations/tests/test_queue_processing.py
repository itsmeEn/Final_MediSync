from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

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
                "/api/operations/queue/start-processing/",
                {"department": "OPD"},
                format="json",
            )

        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        # Queue status should reflect current serving and zero waiting
        self.assertIn("queue_status", data)
        self.assertEqual(data["queue_status"].get("current_serving"), 1)
        self.assertEqual(data["queue_status"].get("total_waiting"), 0)

        # Queue entry should be in progress
        entry = QueueManagement.objects.get(queue_number=1)
        self.assertEqual(entry.status, "in_progress")

        # Notification should be sent over websocket channel
        self.assertIn("notification", data)
        notif = data["notification"]
        self.assertEqual(notif.get("delivery_status"), Notification.DELIVERY_SENT)
        self.assertEqual(notif.get("channel"), Notification.CHANNEL_WEBSOCKET)
        # Message should instruct triage and include department
        self.assertIn("triage room", notif.get("message", ""))
        self.assertIn("OPD", notif.get("message", ""))

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
            "/api/operations/queue/notifications/confirm/",
            {"notification_id": notif.id},
            format="json",
        )

        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertIn("notification", data)
        updated = data["notification"]
        self.assertEqual(updated.get("delivery_status"), Notification.DELIVERY_DELIVERED)
        self.assertIsNotNone(updated.get("delivered_at"))
