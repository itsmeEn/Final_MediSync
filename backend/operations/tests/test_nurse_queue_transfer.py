from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.utils import timezone

from backend.users.models import User, NurseProfile, PatientProfile
from backend.operations.models import QueueStatus, QueueManagement, Notification


class NurseQueueTransferTests(TestCase):
    def setUp(self):
        # Create nurse user
        self.nurse_user = User.objects.create_user(
            email='nurse@example.com', password='testpass', role='nurse', full_name='Nurse Joy'
        )
        self.nurse_profile = NurseProfile.objects.create(user=self.nurse_user, department='OPD')

        # Create patient user + profile
        self.patient_user = User.objects.create_user(
            email='patient@example.com', password='testpass', role='patient', full_name='Gray Niburu'
        )
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user,
            blood_type='O+',
            medical_condition='No condition specified',
            hospital='MediSync General'
        )

        # Open queue for department
        self.queue_status = QueueStatus.objects.create(department='OPD', is_open=True, last_updated_by=self.nurse_user)

        # Add patient to normal queue (waiting)
        self.queue_entry = QueueManagement.objects.create(
            patient=self.patient_profile,
            department='OPD',
            status='waiting',
            queue_number=101,
            position_in_queue=1,
            enqueue_time=timezone.now(),
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.nurse_user)

    def test_start_processing_returns_patient_profile_and_updates_status(self):
        url = reverse('start_queue_processing')  # mapped in backend/operations/urls.py
        resp = self.client.post(url, {'department': 'OPD'}, format='json')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Response contains optional patient_profile for UI transfer
        self.assertIn('patient_profile', data)
        profile = data['patient_profile']
        self.assertIsNotNone(profile)
        self.assertEqual(profile['full_name'], 'Gray Niburu')
        self.assertEqual(profile['department'], 'OPD')

        # Queue status updated
        self.queue_status.refresh_from_db()
        self.assertEqual(self.queue_status.current_serving, 101)

        # Queue entry marked in_progress
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.status, 'in_progress')

        # Notification created
        self.assertTrue(Notification.objects.filter(user=self.patient_user).exists())

    def test_confirm_notification_delivery(self):
        # Create a notification and confirm
        notif = Notification.objects.create(
            user=self.patient_user,
            message='Test delivery',
            channel=Notification.CHANNEL_WEBSOCKET,
            delivery_status=Notification.DELIVERY_SENT,
            sent_at=timezone.now(),
        )

        # Authenticate as patient
        client = APIClient()
        client.force_authenticate(user=self.patient_user)
        url = reverse('confirm_notification_delivery')
        resp = client.post(url, {'notification_id': notif.id}, format='json')

        self.assertEqual(resp.status_code, 200)
        notif.refresh_from_db()
        self.assertEqual(notif.delivery_status, Notification.DELIVERY_DELIVERED)
        self.assertIsNotNone(notif.delivered_at)

