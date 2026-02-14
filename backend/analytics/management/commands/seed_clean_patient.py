
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from backend.users.models import PatientProfile
from backend.analytics.models import PatientRecord, AnalyticsResult

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a robust patient seed profile with corresponding analytics data to prevent NaN values.'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, default='Seed Patient', help='Name of the patient')
        parser.add_argument('--email', type=str, default='seed.patient@example.com', help='Email of the patient')
        parser.add_argument('--records', type=int, default=5, help='Number of historical records to generate for this patient')

    def handle(self, *args, **options):
        name = options['name']
        email = options['email']
        record_count = options['records']

        self.stdout.write(f"Creating seed patient '{name}' ({email})...")

        # 1. Create User
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': name,
                'role': 'patient',
                'is_active': True,
                'is_verified': True,
                'verification_status': 'approved',
                'date_of_birth': (timezone.now() - timedelta(days=365*30)).date(), # 30 years old
                'gender': 'Male',
                'hospital_name': 'General Hospital',
            }
        )
        if created:
            user.set_password('Password123!')
            user.save()
            self.stdout.write(self.style.SUCCESS(f"User created: {user.email}"))
        else:
            self.stdout.write(self.style.WARNING(f"User already exists: {user.email}"))

        # 2. Create/Update PatientProfile
        profile, p_created = PatientProfile.objects.get_or_create(user=user)
        
        # Populate robust profile data
        profile.blood_type = 'O+'
        profile.emergency_contact_name = 'Emergency Contact'
        profile.emergency_contact_number = '555-9999'
        
        # Set standardized nursing intake to prevent empty field issues
        profile.set_nursing_intake({
            'vitals': {'bp': '120/80', 'hr': 72, 'rr': 16, 'temp_c': 37.0, 'o2_sat': 98},
            'chief_complaint': 'Routine checkup',
            'pain_score': 0,
            'fall_risk_score': 0,
            'assessed_at': timezone.now().isoformat(),
            'allergies': [{'substance': 'None', 'reaction': 'None'}],
            'current_medications': ['Multivitamin'],
            'medical_history': ['None significant'],
        })
        profile.save()
        self.stdout.write(self.style.SUCCESS("PatientProfile populated with robust data."))

        # 3. Create PatientRecords for Analytics
        # We need enough records to ensure volume prediction and demographics don't return NaN/Empty
        
        existing_records = PatientRecord.objects.filter(patient=user).count()
        records_to_create = max(0, record_count - existing_records)
        
        if records_to_create > 0:
            self.stdout.write(f"Generating {records_to_create} historical patient records for analytics...")
            
            conditions = ["Hypertension", "Diabetes", "Asthma", "Flu", "Healthy"]
            medications = ["Lisinopril", "Metformin", "Albuterol", "Tamiflu", "None"]
            outcomes = ["Recovered", "Ongoing", "Recovered", "Recovered", "Ongoing"]
            
            today = timezone.now()
            
            for i in range(records_to_create):
                # Spread records over the last 6 months
                days_ago = random.randint(0, 180)
                record_date = today - timedelta(days=days_ago)
                
                PatientRecord.objects.create(
                    patient=user,
                    date_of_admission=record_date,
                    medical_condition=random.choice(conditions),
                    age=30, # Consistent with DOB
                    gender='Male',
                    medication=random.choice(medications),
                    severity=random.choice(['Low', 'Medium']),
                    treatment_outcome=random.choice(outcomes),
                    created_at=record_date,
                    updated_at=record_date
                )
            self.stdout.write(self.style.SUCCESS(f"Created {records_to_create} PatientRecord entries."))
        else:
            self.stdout.write("Patient already has sufficient historical records.")

        # 4. Trigger Analytics Refresh
        self.stdout.write("Refreshing basic analytics results...")
        try:
            # We assume populate_demo_data might be broken or not needed since we implemented safe regeneration
            self._regenerate_analytics()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to refresh analytics: {e}"))

    def _regenerate_analytics(self):
        """
        Regenerate analytics results ensuring no NaNs are produced.
        """
        # 1. Demographics
        records = PatientRecord.objects.all()
        total = records.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No records found for analytics."))
            return

        age_sum = sum(r.age for r in records if r.age)
        avg_age = round(age_sum / total, 1) if total > 0 else 0
        
        # Gender
        gender_counts = {}
        for r in records:
            g = r.gender or 'Other'
            gender_counts[g] = gender_counts.get(g, 0) + 1
        
        demographics_data = {
            "age_distribution": {"0-18": 0, "19-35": 0, "36-50": 0, "51-65": 0, "65+": 0}, # Fill based on actuals
            "gender_proportions": gender_counts,
            "total_patients": total,
            "average_age": avg_age
        }
        
        # Populate age bins
        for r in records:
            a = r.age or 0
            if a <= 18: demographics_data["age_distribution"]["0-18"] += 1
            elif a <= 35: demographics_data["age_distribution"]["19-35"] += 1
            elif a <= 50: demographics_data["age_distribution"]["36-50"] += 1
            elif a <= 65: demographics_data["age_distribution"]["51-65"] += 1
            else: demographics_data["age_distribution"]["65+"] += 1

        AnalyticsResult.objects.create(
            analysis_type="patient_demographics",
            status="completed",
            results=demographics_data
        )
        self.stdout.write("Updated patient_demographics.")

        # 2. Volume Prediction (Safe Version)
        # Ensure we have at least some data points for the graph
        daily_counts = {}
        for r in records:
            d = r.date_of_admission.date().strftime("%Y-%m-%d")
            daily_counts[d] = daily_counts.get(d, 0) + 1
        
        days_sorted = sorted(daily_counts.items())
        
        # Generate safe forecast
        forecasted = []
        today = timezone.now().date()
        
        # Calculate baseline average (handle empty case)
        if days_sorted:
            avg_daily = sum(c for _, c in days_sorted) / len(days_sorted)
        else:
            avg_daily = 0
            
        # Generate next 7 days
        for i in range(1, 8):
            next_day = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            # Add slight jitter to average for realism, ensure non-negative
            val = max(0, int(avg_daily * random.uniform(0.8, 1.2)))
            forecasted.append({
                "date": next_day,
                "predicted": val,
                "actual": None
            })
            
        volume_data = {
            "forecasted_data": forecasted,
            "evaluation_metrics": {"mae": 0.5, "rmse": 0.8}, # Dummy safe metrics
            "comparison_data": [{"date": d, "predicted": c, "actual": c} for d, c in days_sorted[-14:]] # Last 2 weeks
        }
        
        AnalyticsResult.objects.create(
            analysis_type="patient_volume_prediction",
            status="completed",
            results=volume_data
        )
        self.stdout.write("Updated patient_volume_prediction.")

        # 3. Medication Analysis
        med_counts = {}
        for r in records:
            if r.medication and r.medication != 'None':
                med_counts[r.medication] = med_counts.get(r.medication, 0) + 1
        
        pareto = sorted([{"medication": k, "prescriptions": v} for k, v in med_counts.items()], key=lambda x: x["prescriptions"], reverse=True)
        medication_data = {
            "medication_pareto_data": pareto[:20],
            "medication_usage": pareto,
        }
        AnalyticsResult.objects.create(
            analysis_type="medication_analysis",
            status="completed",
            results=medication_data
        )
        self.stdout.write("Updated medication_analysis.")
        
        # 4. Health Trends (Top Illnesses)
        cond_counts = {}
        for r in records:
            if r.medical_condition:
                cond_counts[r.medical_condition] = cond_counts.get(r.medical_condition, 0) + 1
                
        common_conditions = [c for c, _ in sorted(cond_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        trends_data = {
            "top_illnesses_by_week": [
                {"medical_condition": c, "count": cond_counts[c], "week": "Current"}
                for c in common_conditions
            ],
            "trend_analysis": {"status": "stable"}
        }
        AnalyticsResult.objects.create(
            analysis_type="health_trends",
            status="completed",
            results=trends_data
        )
        self.stdout.write("Updated health_trends.")

