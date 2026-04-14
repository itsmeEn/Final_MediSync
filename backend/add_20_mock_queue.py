import os
import sys
import django
import random
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.users.models import User, PatientProfile
from backend.operations.models import QueueManagement, QueueStatus

def generate_random_dob():
    start_date = date(1950, 1, 1)
    end_date = date(2010, 12, 31)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

def run():
    print("Generating 20 mock patients for OPD queue...")
    
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin']
    blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    conditions = ['Fever and Cough', 'Sprained Ankle', 'Migraine', 'Routine Checkup', 'Hypertension Follow-up', 'Mild Allergic Reaction', 'Stomach Pain', 'Back Pain', 'Skin Rash', 'Seasonal Flu']
    
    # Start queue numbering from where it might have left off, or 100
    starting_queue = 100
    
    # Track how many added
    added_count = 0

    for i in range(20):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        gender = random.choice(['Male', 'Female'])
        
        # Create User
        email = f"mock.patient{i}@medisync.local"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': f"{fname} {lname}",
                'role': 'patient',
                'is_verified': True,
                'verification_status': 'approved',
                'date_of_birth': generate_random_dob(),
                'gender': gender
            }
        )
        if created:
            user.set_password('password123')
            user.save()

        # Create Profile
        profile, p_created = PatientProfile.objects.get_or_create(
            user=user,
            defaults={
                'blood_type': random.choice(blood_types),
                'medical_condition': random.choice(conditions),
                'hospital': 'MediSync General Hospital'
            }
        )

        # 1 in 5 chance of being a priority patient
        is_priority = random.random() < 0.2

        # Add to Queue
        queue_entry, q_created = QueueManagement.objects.get_or_create(
            patient=profile,
            department='OPD',
            status='waiting',
            defaults={
                'queue_number': starting_queue + i,
                'is_priority': is_priority,
            }
        )
        if q_created:
            added_count += 1
            print(f"Added #{queue_entry.queue_number} - {user.full_name} (Priority: {is_priority})")

    # Update Queue Status
    qs, qs_created = QueueStatus.objects.get_or_create(department='OPD', defaults={'is_open': True})
    qs.is_open = True
    total = QueueManagement.objects.filter(department='OPD', status='waiting').count()
    qs.total_waiting = total
    qs.save()
    
    print(f"\nSuccessfully generated {added_count} patients!")
    print(f"Total currently waiting in OPD: {total}")

if __name__ == '__main__':
    run()