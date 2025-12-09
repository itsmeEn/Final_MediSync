from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from backend.users.models import User, PatientProfile, GeneralDoctorProfile


class HospitalDepartmentsTests(TestCase):
    def setUp(self):
        # Users
        self.patient_user = User.objects.create_user(
            email='patient@example.com', password='pass', role='patient', full_name='Test Patient'
        )
        PatientProfile.objects.create(user=self.patient_user, hospital='MediSync General')

        self.nurse_user = User.objects.create_user(
            email='nurse@example.com', password='pass', role='nurse', full_name='Nurse Test', verification_status='approved'
        )

        self.client = APIClient()

    def test_patient_sees_departments_from_verified_doctors(self):
        # Approved doctors in same hospital
        doc1_user = User.objects.create_user(
            email='doc1@example.com', password='pass', role='doctor', full_name='Doc One', verification_status='approved', hospital_name='MediSync General'
        )
        GeneralDoctorProfile.objects.create(user=doc1_user, specialization='cardiology', available_for_consultation=True)

        doc2_user = User.objects.create_user(
            email='doc2@example.com', password='pass', role='doctor', full_name='Doc Two', verification_status='approved', hospital_name='MediSync General'
        )
        GeneralDoctorProfile.objects.create(user=doc2_user, specialization='dermatology', available_for_consultation=True)

        self.client.force_authenticate(user=self.patient_user)
        url = reverse('hospital_departments')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        values = {d['value'] for d in data.get('departments', [])}
        self.assertIn('cardiology', values)
        self.assertIn('dermatology', values)

    def test_non_patient_requires_approval(self):
        # Pending nurse should be forbidden
        pending_nurse = User.objects.create_user(
            email='nurse2@example.com', password='pass', role='nurse', full_name='Pending Nurse', verification_status='pending'
        )
        self.client.force_authenticate(user=pending_nurse)
        url = reverse('hospital_departments')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_fallback_defaults_when_no_doctors(self):
        self.client.force_authenticate(user=self.patient_user)
        url = reverse('hospital_departments')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        values = {d['value'] for d in data.get('departments', [])}
        self.assertIn('general-medicine', values)

    def test_hospital_query_param_scopes_results(self):
        # Create doctors in two hospitals
        docA_user = User.objects.create_user(
            email='docA@example.com', password='pass', role='doctor', full_name='Doc A', verification_status='approved', hospital_name='Hospital A'
        )
        GeneralDoctorProfile.objects.create(user=docA_user, specialization='oncology', available_for_consultation=True)

        docB_user = User.objects.create_user(
            email='docB@example.com', password='pass', role='doctor', full_name='Doc B', verification_status='approved', hospital_name='Hospital B'
        )
        GeneralDoctorProfile.objects.create(user=docB_user, specialization='orthopedics', available_for_consultation=True)

        # Approved nurse can query with ?hospital=Hospital A
        self.client.force_authenticate(user=self.nurse_user)
        url = reverse('hospital_departments') + '?hospital=Hospital A'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        values = {d['value'] for d in data.get('departments', [])}
        self.assertIn('oncology', values)
        self.assertNotIn('orthopedics', values)

