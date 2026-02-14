
import os
import sys
import django
import io
from reportlab.lib.pagesizes import letter

# Setup Django environment
sys.path.append('/Users/judeibardaloza/Desktop/Final_MediSync')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.operations.pdf_templates.doctor_analytics import DoctorAnalyticsPDF
from backend.operations.pdf_templates.nurse_analytics import NurseAnalyticsPDF

def verify_doctor_pdf():
    print("Verifying Doctor PDF...")
    buffer = io.BytesIO()
    
    # Mock data structure matching views.py
    data = {
        'analytics_results': {
            'metrics': {'Total Patients': '120', 'Predicted Volume': '145'},
            'visualization': None, # Can mock an image if needed
            'comparative_data': [
                ['Metric', 'Current', 'Benchmark', 'Status'],
                ['Forecast MAE', '4.20', '5.00', 'Good'],
                ['Forecast RMSE', '6.10', '7.00', 'Good'],
                ['Model Accuracy', 'High', 'High', 'Optimal']
            ]
        },
        'performance_factors': {
            'significant_factors': ['Wait Time: 0.85', 'Staffing: 0.72'],
            'correlation_matrix': None,
            'trend_analysis': None,
            'detailed_metrics': [
                ['Date', 'Actual Vol', 'Forecasted', 'Diff'],
                ['2023-10-01', '100', '95', '5.0'],
                ['2023-10-02', '110', '108', '2.0']
            ]
        },
        'ai_recommendations': {
            'actionable': [{'text': 'Increase staff', 'confidence': 0.9}],
            'predictive': [{'text': 'High volume expected', 'confidence': 0.85}],
            'strategies': [{'text': 'Optimize triage', 'confidence': 0.8}],
            'resource': [{'text': 'Add 2 nurses', 'confidence': 0.92}]
        }
    }
    
    hospital_info = {'name': 'Test Hospital', 'address': '123 Test St'}
    user_info = {'name': 'Dr. Smith', 'role': 'Doctor', 'specialization': 'Cardiology'}
    
    try:
        pdf = DoctorAnalyticsPDF(buffer, hospital_info, user_info)
        pdf.generate(data)
        print("Doctor PDF generated successfully. Size:", len(buffer.getvalue()))
    except Exception as e:
        print(f"FAILED to generate Doctor PDF: {e}")
        import traceback
        traceback.print_exc()

def verify_nurse_pdf():
    print("\nVerifying Nurse PDF...")
    buffer = io.BytesIO()
    
    data = {
        'analytics_results': {
            'metrics': {'Patients Attended': '45', 'Meds Administered': '200'},
            'medication_records': {'Antibiotics': 50, 'Painkillers': 30},
            'visualization': None,
            'comparative_data': [
                ['Metric', 'Current', 'Target', 'Status'],
                ['Med Admin Accuracy', '99.5%', '99.9%', 'On Track'],
                ['Shift Coverage', 'Full', 'Full', 'Optimal']
            ]
        },
        'performance_factors': {
            'significant_factors': ['Shift Duration: 0.65'],
            'correlation_matrix': None,
            'trend_analysis': None,
            'detailed_metrics': [
                ['Date', 'Est. Patient Load', 'Staffing', 'Status'],
                ['2023-10-01', '40', 'Full', 'Normal'],
                ['2023-10-02', '55', 'Short', 'High Load']
            ]
        },
        'ai_recommendations': {
            'actionable': [{'text': 'Check inventory', 'confidence': 0.88}],
            'predictive': [{'text': 'Supply shortage likely', 'confidence': 0.75}],
            'strategies': [{'text': 'Batch processing', 'confidence': 0.82}],
            'resource': [{'text': 'Restock Station A', 'confidence': 0.95}]
        }
    }
    
    hospital_info = {'name': 'Test Hospital', 'address': '123 Test St'}
    user_info = {'name': 'Nurse Jones', 'role': 'Nurse', 'department': 'ER'}
    
    try:
        pdf = NurseAnalyticsPDF(buffer, hospital_info, user_info)
        pdf.generate(data)
        print("Nurse PDF generated successfully. Size:", len(buffer.getvalue()))
    except Exception as e:
        print(f"FAILED to generate Nurse PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_doctor_pdf()
    verify_nurse_pdf()
