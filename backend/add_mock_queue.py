import os
import sys
import django
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.users.models import User, PatientProfile
from backend.operations.models import QueueManagement, QueueStatus

def run():
    print("Creating mock patient...")
    user, created = User.objects.get_or_create(
        email='mock.patient@medisync.local',
        defaults={
            'full_name': 'Mock Patient (OPD)',
            'role': 'patient',
            'is_verified': True,
            'verification_status': 'approved',
            'date_of_birth': date(1985, 5, 15),
            'gender': 'Male'
        }
    )
    if created:
        user.set_password('password123')
        user.save()
        print("Created new User: Mock Patient (OPD)")

    profile, p_created = PatientProfile.objects.get_or_create(
        user=user,
        defaults={
            'blood_type': 'O+',
            'medical_condition': 'Hypertension, Mild Asthma',
            'hospital': 'MediSync General Hospital'
        }
    )
    if p_created: print("Created PatientProfile")

    print("Adding to OPD Queue...")
    queue_entry, q_created = QueueManagement.objects.get_or_create(
        patient=profile,
        department='OPD',
        status='waiting',
        defaults={
            'queue_number': 999,
            'is_priority': False,
        }
    )
    
    if q_created:
        print(f"Successfully added to queue! Queue Number: {queue_entry.queue_number}")
    else:
        print(f"Patient is already in the queue: {queue_entry.queue_number}")

    qs, qs_created = QueueStatus.objects.get_or_create(department='OPD', defaults={'is_open': True})
    qs.is_open = True
    total = QueueManagement.objects.filter(department='OPD', status='waiting').count()
    qs.total_waiting = total
    qs.save()
    print(f"Total waiting in OPD: {total}")

if __name__ == '__main__':
    run()