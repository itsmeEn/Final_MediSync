
from django.core.management.base import BaseCommand
import io
import matplotlib.pyplot as plt
from backend.operations.pdf_templates import DoctorAnalyticsPDF, NurseAnalyticsPDF, PatientArchivePDF
import os

class Command(BaseCommand):
    help = 'Generates sample PDFs for Doctor, Nurse, and Patient Archive.'

    def handle(self, *args, **options):
        self.stdout.write("Generating sample PDFs...")

        # Common Mock Info
        hospital_info = {
            'name': 'MediSync General Hospital',
            'address': '123 Healthcare Blvd, Medical District, NY 10001',
        }
        
        # Logo Path
        logo_path = 'frontend/src/assets/logo.png'
        abs_logo_path = os.path.join(os.getcwd(), logo_path)
        if not os.path.exists(abs_logo_path):
             self.stdout.write(self.style.WARNING(f"Logo not found at {abs_logo_path}"))
             abs_logo_path = None

        # 1. Generate Doctor Analytics Report
        self.stdout.write("Generating Doctor Analytics Report...")
        doc_buffer = io.BytesIO()
        
        # Mock Doctor Data
        # Chart
        plt.figure(figsize=(6, 3), dpi=300)
        plt.bar(['Flu', 'Cov', 'Cold'], [50, 30, 20], color='gray')
        plt.title('Diagnosis Distribution')
        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png', bbox_inches='tight')
        chart_buffer.seek(0)
        plt.close()
        
        doctor_data = {
            'medical_statistics': {'Total Patients': 145, 'Critical Cases': 12, 'Avg Stay': '4 Days'},
            'diagnosis_patterns': {'chart': chart_buffer},
            'treatment_analytics': "Antibiotic usage has decreased by 15% this quarter due to stricter protocols.",
            'ai_interpretations': [
                "High correlation between seasonal changes and respiratory admissions.",
                "Recommend increasing staff for upcoming flu season."
            ]
        }
        
        doc_gen = DoctorAnalyticsPDF(doc_buffer, hospital_info, logo_path=abs_logo_path)
        doc_gen.generate(doctor_data)
        
        with open('sample_doctor_analytics.pdf', 'wb') as f:
            f.write(doc_buffer.getvalue())

        # 2. Generate Nurse Analytics Report
        self.stdout.write("Generating Nurse Analytics Report...")
        nurse_buffer = io.BytesIO()
        
        nurse_data = {
            'care_metrics': {'Avg Response Time': '3.5 min', 'Patients per Nurse': '5', 'Satisfaction Score': '4.8/5'},
            'medication_records': [
                ['Time', 'Patient', 'Medication', 'Status'],
                ['08:00', 'John Doe', 'Aspirin', 'Administered'],
                ['09:30', 'Jane Smith', 'Insulin', 'Administered'],
                ['10:15', 'Bob Wilson', 'Antibiotic', 'Delayed']
            ],
            'ai_interpretations': "Medication rounds are most delayed between 10:00 AM and 11:00 AM. Suggest schedule adjustment."
        }
        
        nurse_gen = NurseAnalyticsPDF(nurse_buffer, hospital_info, logo_path=abs_logo_path)
        nurse_gen.generate(nurse_data)
        
        with open('sample_nurse_analytics.pdf', 'wb') as f:
            f.write(nurse_buffer.getvalue())

        # 3. Generate Patient Archive Document
        self.stdout.write("Generating Patient Archive Document...")
        archive_buffer = io.BytesIO()
        
        archive_data = {
            'patient_info': {'name': 'Alice Wonderland', 'id': 'P-9988', 'dob': '1990-05-12', 'blood_group': 'O+'},
            'medical_history': [
                {'date': '2020-01-10', 'condition': 'Appendicitis', 'notes': 'Surgical removal successful.'},
                {'date': '2022-06-15', 'condition': 'Mild Concussion', 'notes': 'Observation for 24 hours.'}
            ],
            'test_results': [
                {'date': '2023-11-01', 'name': 'CBC', 'result': 'Normal', 'range': 'N/A'},
                {'date': '2023-11-01', 'name': 'Blood Sugar', 'result': '95 mg/dL', 'range': '70-100'}
            ],
            'treatment_timeline': [
                {'date': '2023-11-01', 'event': 'Admitted for routine checkup'},
                {'date': '2023-11-02', 'event': 'Labs collected'},
                {'date': '2023-11-03', 'event': 'Discharged'}
            ]
        }
        
        archive_gen = PatientArchivePDF(archive_buffer, hospital_info, logo_path=abs_logo_path)
        archive_gen.generate(archive_data)
        
        with open('sample_patient_archive.pdf', 'wb') as f:
            f.write(archive_buffer.getvalue())

        self.stdout.write(self.style.SUCCESS("Successfully generated all sample PDFs."))
