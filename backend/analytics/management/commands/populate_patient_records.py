from django.core.management.base import BaseCommand
from django.utils import timezone
from backend.analytics.models import PatientRecord
from backend.users.models import User
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Populate database with sample patient records for analytics testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of patient records to create (default: 100)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing patient records before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            PatientRecord.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing patient records'))

        count = options['count']
        
        # Get existing users (patients)
        patients = User.objects.filter(role='patient')
        if not patients.exists():
            self.stdout.write(self.style.ERROR('No patient users found. Please create some patient accounts first.'))
            return

        # Medical conditions and medications
        medical_conditions = [
            'Hypertension', 'Diabetes', 'Heart Disease', 'Asthma', 'Arthritis',
            'Depression', 'Anxiety', 'Obesity', 'High Cholesterol', 'Migraine',
            'Pneumonia', 'Bronchitis', 'Flu', 'Cold', 'Fever',
            'Gastroenteritis', 'Appendicitis', 'Fracture', 'Sprain', 'Burn'
        ]
        
        medications = [
            'Metformin', 'Lisinopril', 'Atorvastatin', 'Omeprazole', 'Albuterol',
            'Sertraline', 'Lorazepam', 'Ibuprofen', 'Acetaminophen', 'Aspirin',
            'Amoxicillin', 'Ciprofloxacin', 'Prednisone', 'Warfarin', 'Insulin',
            'Furosemide', 'Digoxin', 'Morphine', 'Codeine', 'Tramadol'
        ]

        self.stdout.write(f'Creating {count} patient records for analytics testing...')
        
        created_count = 0
        for i in range(count):
            try:
                # Get a random patient
                patient = random.choice(patients)
                
                # Generate random date within the last 2 years
                start_date = datetime.now() - timedelta(days=730)
                random_date = start_date + timedelta(days=random.randint(0, 730))
                
                # Create patient record
                PatientRecord.objects.create(
                    patient=patient,
                    date_of_admission=random_date,
                    medical_condition=random.choice(medical_conditions),
                    age=random.randint(18, 80),
                    gender=random.choice(['Male', 'Female', 'Other']),
                    medication=random.choice(medications) if random.random() > 0.3 else None,
                    severity=random.choice(['Low', 'Medium', 'High', 'Critical']),
                    treatment_outcome=random.choice(['Recovered', 'Ongoing', 'Transferred', 'Deceased']),
                )
                created_count += 1
                
            except Exception as e:
                self.stdout.write(f'Error creating record {i}: {str(e)}')
                continue

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} patient records for analytics!')
        )
