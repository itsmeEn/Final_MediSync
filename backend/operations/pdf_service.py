import io
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from datetime import datetime
from django.core.mail import EmailMessage
from django.conf import settings
from .models import PatientAssessmentArchive
from .pdf_templates import DoctorAnalyticsPDF, NurseAnalyticsPDF, PatientArchivePDF

# Import analytics PDF components for standardized formatting
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    PLATYPUS_AVAILABLE = True
except ImportError:
    PLATYPUS_AVAILABLE = False

try:
    from PyPDF2 import PdfReader, PdfWriter
except Exception:  # pragma: no cover
    PdfReader = None
    PdfWriter = None


def generate_records_pdf(patient_name: str, patient_email: str, details: Dict[str, Any]) -> bytes:
    """
    Generate a simple PDF containing requested medical records summary using reportlab.
    Returns raw PDF bytes (unencrypted).
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 1 * inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, y, "MediSync Medical Records")
    y -= 0.4 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    y -= 0.3 * inch
    c.drawString(1 * inch, y, f"Patient: {patient_name}")
    y -= 0.25 * inch
    c.drawString(1 * inch, y, f"Email: {patient_email}")
    y -= 0.4 * inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "Request Details")
    y -= 0.3 * inch
    c.setFont("Helvetica", 11)

    def draw_wrapped(text: str, x: float, y: float, max_width: float) -> float:
        from reportlab.pdfbase.pdfmetrics import stringWidth
        words = text.split()
        line = ""
        for w in words:
            if stringWidth(line + (" " if line else "") + w, "Helvetica", 11) > max_width:
                c.drawString(x, y, line)
                y -= 14
                line = w
            else:
                line = (line + " " + w) if line else w
        if line:
            c.drawString(x, y, line)
            y -= 14
        return y

    for key, value in details.items():
        val = value
        if isinstance(value, (dict, list)):
            import json
            val = json.dumps(value, indent=2)[:4000]
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1 * inch, y, f"- {key}:")
        y -= 14
        c.setFont("Helvetica", 11)
        y = draw_wrapped(str(val), 1.2 * inch, y, width - 2.2 * inch)
        y -= 4
        if y < 1 * inch:
            c.showPage()
            y = height - 1 * inch

    c.showPage()
    c.save()
    return buffer.getvalue()


def _get_archive_hospital_information(user, record):
    """Get hospital information for archive PDF header"""
    hospital_name = (record.hospital_name or (getattr(user, 'hospital_name', '') or '')).strip() or "Hospital"
    hospital_address = str(getattr(user, 'hospital_address', '') or '').strip() or "Address not available"
    
    return {
        'name': hospital_name,
        'address': hospital_address,
        'phone': getattr(user, 'hospital_phone', '') or '',
        'email': getattr(user, 'hospital_email', '') or ''
    }


def _get_archive_user_information(user, record):
    """Get user information for archive PDF header"""
    return {
        'name': getattr(user, 'full_name', '') or 'Unknown User',
        'role': getattr(user, 'role', '') or 'Healthcare Provider',
        'department': getattr(user, 'department', '') or '',
        'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    }


def _get_archive_custom_styles():
    """Get custom styles matching analytics PDF format"""
    if not PLATYPUS_AVAILABLE:
        return {}
    
    styles = getSampleStyleSheet()
    
    # Hospital branding styles
    styles.add(ParagraphStyle(
        name='HospitalName',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=6,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold',
        alignment=TA_LEFT
    ))
    
    styles.add(ParagraphStyle(
        name='HospitalAddress',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=12,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica',
        alignment=TA_LEFT
    ))
    
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=6,
        textColor=colors.HexColor('#34495e'),
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='UserInfo',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=12,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica',
        alignment=TA_RIGHT
    ))
    
    styles.add(ParagraphStyle(
        name='DepartmentHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=16,
        textColor=colors.HexColor('#2980b9'),
        fontName='Helvetica-Bold',
        alignment=TA_LEFT
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=6,
        spaceBefore=12,
        textColor=colors.HexColor('#27ae60'),
        fontName='Helvetica-Bold',
        alignment=TA_LEFT
    ))
    
    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        parent=styles['Heading4'],
        fontSize=11,
        spaceAfter=4,
        spaceBefore=8,
        textColor=colors.HexColor('#8e44ad'),
        fontName='Helvetica-Bold',
        alignment=TA_LEFT
    ))
    
    styles.add(ParagraphStyle(
        name='ContentText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica',
        alignment=TA_LEFT,
        leftIndent=12
    ))
    
    styles.add(ParagraphStyle(
        name='FooterText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#95a5a6'),
        fontName='Helvetica',
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='HighlightText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#e74c3c'),
        fontName='Helvetica-Bold',
        alignment=TA_LEFT
    ))
    
    return styles


def _create_archive_pdf_template(buffer, hospital_info, user_info):
    """Create standardized PDF template matching analytics format"""
    if not PLATYPUS_AVAILABLE:
        return None
    
    # Responsive page size and margins
    page_width, page_height = A4
    margin = 0.75 * inch
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=f"Patient Assessment Archive - {hospital_info.get('name', 'Hospital')}",
        author=user_info.get('name', 'Healthcare Provider'),
        subject="Patient Assessment Archive Report",
        creator="MediSync Healthcare Management System"
    )
    
    return doc


def _add_archive_standardized_header(story, hospital_info, user_info, report_title, styles):
    """Add standardized header matching analytics format"""
    if not PLATYPUS_AVAILABLE:
        return
    
    # Hospital name
    story.append(Paragraph(hospital_info.get('name', 'Hospital'), styles['HospitalName']))
    
    # Hospital address
    story.append(Paragraph(hospital_info.get('address', 'Address not available'), styles['HospitalAddress']))
    
    # Report title
    story.append(Paragraph(report_title, styles['ReportTitle']))
    
    # User information
    user_text = f"Generated by: {user_info.get('name', 'Unknown User')} ({user_info.get('role', 'Healthcare Provider')})"
    if user_info.get('department'):
        user_text += f" - {user_info['department']}"
    user_text += f"<br/>Generated on: {user_info.get('generated_at', 'Unknown Date')}"
    
    story.append(Paragraph(user_text, styles['UserInfo']))
    
    # Separator line
    story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.HexColor('#bdc3c7')))
    story.append(Spacer(1, 12))


def _add_patient_demographics_section(story, user, profile, record, styles):
    """Add patient demographics section"""
    if not PLATYPUS_AVAILABLE:
        return
    
    story.append(Paragraph("Patient Demographics", styles['DepartmentHeader']))
    
    # Patient information
    full_name = getattr(user, 'full_name', '') or 'Unknown Patient'
    dob = getattr(user, 'date_of_birth', None)
    dob_str = dob.strftime('%Y-%m-%d') if dob else 'Not specified'
    gender = getattr(user, 'gender', '') or 'Not specified'
    blood_type = getattr(profile, 'blood_type', '') if profile else ''
    
    demographics_data = [
        ['Patient Name:', full_name],
        ['Date of Birth:', dob_str],
        ['Gender:', gender],
    ]
    
    if blood_type:
        demographics_data.append(['Blood Type:', blood_type])
    
    # Create table for demographics
    demographics_table = Table(demographics_data, colWidths=[2*inch, 4*inch])
    demographics_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#34495e')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    story.append(demographics_table)
    story.append(Spacer(1, 12))


def _add_assessment_context_section(story, record, styles):
    """Add assessment context section"""
    if not PLATYPUS_AVAILABLE:
        return
    
    story.append(Paragraph("Assessment Context", styles['DepartmentHeader']))
    
    context_data = [
        ['Assessment Type:', record.assessment_type or 'Not specified'],
        ['Medical Condition:', record.medical_condition or 'Not specified'],
    ]
    
    if record.last_assessed_at:
        context_data.append(['Last Assessed:', record.last_assessed_at.strftime('%Y-%m-%d %H:%M:%S')])
    
    # Create table for context
    context_table = Table(context_data, colWidths=[2*inch, 4*inch])
    context_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#34495e')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    story.append(context_table)
    story.append(Spacer(1, 16))


def _add_archive_forms_sections(story, profile, record, styles):
    """Add forms sections (exclude discharge and patient education)"""
    if not PLATYPUS_AVAILABLE:
        return
    
    story.append(Paragraph("Medical Forms and Records", styles['DepartmentHeader']))
    
    # Forms to include (exclude discharge and patient education)
    forms = []
    if profile:
        forms.extend([
            ("Nursing Intake & Assessment", getattr(profile, 'nursing_intake_assessment', {}) or {}),
            ("Graphic Flow Sheets", list(getattr(profile, 'graphic_flow_sheets', []) or [])),
            ("Medication Administration Records", list(getattr(profile, 'medication_administration_records', []) or [])),
            ("History & Physical Forms", list(getattr(profile, 'history_physical_forms', []) or [])),
            ("Progress Notes", list(getattr(profile, 'progress_notes', []) or [])),
            ("Provider Order Sheets", list(getattr(profile, 'provider_order_sheets', []) or [])),
            ("Operative/Procedure Reports", list(getattr(profile, 'operative_procedure_reports', []) or [])),
        ])
    
    # Add assessment snapshot data (excluding discharge and patient education)
    try:
        assessment_snapshot = record.assessment_data or {}
        if isinstance(assessment_snapshot, dict):
            excluded = {"discharge_checklist_summary", "patient_education_record"}
            known_sections = {
                "nursing_intake_assessment", "graphic_flow_sheets", "medication_administration_records",
                "history_physical_forms", "progress_notes", "provider_order_sheets", "operative_procedure_reports"
            }
            for k, v in assessment_snapshot.items():
                if k in excluded or k in known_sections:
                    continue
                forms.append((k.replace('_', ' ').title(), v))
    except Exception:
        pass
    
    # Render each form section
    for title, data in forms:
        _add_form_section(story, title, data, styles)
    
    if not forms:
        story.append(Paragraph("No medical forms available for this archived assessment.", styles['ContentText']))


def _add_form_section(story, title, data, styles):
    """Add individual form section with proper formatting"""
    if not PLATYPUS_AVAILABLE:
        return
    
    story.append(Paragraph(title, styles['SectionHeader']))
    
    if not data:
        story.append(Paragraph("No data available", styles['ContentText']))
        story.append(Spacer(1, 8))
        return
    
    if isinstance(data, dict):
        _add_dict_content(story, data, styles)
    elif isinstance(data, list):
        _add_list_content(story, data, styles)
    else:
        story.append(Paragraph(str(data), styles['ContentText']))
    
    story.append(Spacer(1, 12))


def _add_dict_content(story, data_dict, styles):
    """Add dictionary content as formatted table"""
    if not PLATYPUS_AVAILABLE or not data_dict:
        return
    
    table_data = []
    for key, value in data_dict.items():
        formatted_key = key.replace('_', ' ').title()
        if isinstance(value, (dict, list)):
            formatted_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
        else:
            formatted_value = str(value) if value is not None else "Not specified"
        table_data.append([formatted_key, formatted_value])
    
    if table_data:
        content_table = Table(table_data, colWidths=[2*inch, 4*inch])
        content_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#34495e')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ecf0f1')),
        ]))
        story.append(content_table)


def _add_list_content(story, data_list, styles):
    """Add list content as formatted entries"""
    if not PLATYPUS_AVAILABLE or not data_list:
        return
    
    for i, item in enumerate(data_list, 1):
        story.append(Paragraph(f"Entry {i}:", styles['SubsectionHeader']))
        if isinstance(item, dict):
            _add_dict_content(story, item, styles)
        else:
            story.append(Paragraph(str(item), styles['ContentText']))
        story.append(Spacer(1, 6))


def _add_archive_standardized_footer(story, styles):
    """Add standardized footer matching analytics format"""
    if not PLATYPUS_AVAILABLE:
        return
    
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.HexColor('#bdc3c7')))
    story.append(Spacer(1, 6))
    
    footer_text = """
    <b>CONFIDENTIAL MEDICAL RECORD</b><br/>
    This document contains confidential patient health information protected by HIPAA and other applicable privacy laws. 
    Unauthorized access, use, or disclosure is strictly prohibited and may result in civil and criminal penalties. 
    This archive was generated for authorized healthcare personnel only.<br/><br/>
    
    <i>Generated by MediSync Healthcare Management System</i>
    """
    
    story.append(Paragraph(footer_text, styles['FooterText']))


def encrypt_pdf_aes256(pdf_bytes: bytes, password: str) -> bytes:
    """
    Encrypt PDF bytes using AES-256 (requires PyPDF2 >= 3.0.0).
    """
    if PdfReader is None or PdfWriter is None:
        raise RuntimeError("PyPDF2 is required for AES-256 PDF encryption. Please install it.")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    try:
        writer.encrypt(user_password=password, owner_password=password, use_128bit=False)
    except TypeError:
        writer.encrypt(password)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()


def send_encrypted_pdf_to_patient(patient_email: str, encrypted_pdf: bytes, filename: str, message: str = None):
    subject = "Your Requested Medical Records (Encrypted PDF)"
    body = message or (
        "Attached is your encrypted medical records PDF. "
        "Use the provided password format to open it."
    )
    email = EmailMessage(subject, body, getattr(settings, 'DEFAULT_FROM_EMAIL', None), [patient_email])
    email.attach(filename, encrypted_pdf, 'application/pdf')
    email.send(fail_silently=False)


def _draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, font_name: str = "Helvetica", font_size: int = 11) -> float:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = (text or "").split()
    line = ""
    for w in words:
        if stringWidth(line + (" " if line else "") + w, font_name, font_size) > max_width:
            c.drawString(x, y, line)
            y -= 14
            line = w
        else:
            line = (line + " " + w) if line else w
    if line:
        c.drawString(x, y, line)
        y -= 14
    return y


def _draw_section_json(c: canvas.Canvas, title: str, data: Any, width: float, y: float) -> float:
    import json
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, title)
    y -= 16
    c.setFont("Helvetica", 11)
    try:
        serialized = json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        serialized = str(data)
    # Limit overly long sections to keep file manageable
    if len(serialized) > 20000:
        serialized = serialized[:20000] + "\n... (truncated)"
    for line in serialized.split("\n"):
        y = _draw_wrapped(c, line, 1.2 * inch, y, width - 2.2 * inch)
        if y < 1 * inch:
            c.showPage()
            y = A4[1] - 1 * inch
    y -= 8
    return y


def _map_archive_to_pdf_data(record: PatientAssessmentArchive) -> Dict[str, Any]:
    """Map archive record to data structure for PatientArchivePDF"""
    user = getattr(record, 'user', None)
    profile = getattr(record, 'patient_profile', None)
    
    # 1. Patient Info
    patient_info = {
        'name': getattr(user, 'full_name', 'Unknown Patient'),
        'dob': getattr(user, 'date_of_birth', 'Not specified'),
        'gender': getattr(user, 'gender', 'Not specified'),
        'blood_group': getattr(profile, 'blood_type', '') if profile else ''
    }
    
    # 2. Assessment Context
    assessment_context = {
        'assessment_type': record.assessment_type or 'Not specified',
        'medical_condition': record.medical_condition or 'Not specified',
        'last_assessed': record.last_assessed_at.strftime('%Y-%m-%d %H:%M:%S') if record.last_assessed_at else 'Not specified'
    }
    
    # 3. Dynamic Sections
    sections = []
    
    # From profile
    if profile:
        profile_sections = [
            ("Nursing Intake & Assessment", getattr(profile, 'nursing_intake_assessment', {})),
            ("Graphic Flow Sheets", list(getattr(profile, 'graphic_flow_sheets', []) or [])),
            ("Medication Administration Records", list(getattr(profile, 'medication_administration_records', []) or [])),
            ("History & Physical Forms", list(getattr(profile, 'history_physical_forms', []) or [])),
            ("Progress Notes", list(getattr(profile, 'progress_notes', []) or [])),
            ("Provider Order Sheets", list(getattr(profile, 'provider_order_sheets', []) or [])),
            ("Operative/Procedure Reports", list(getattr(profile, 'operative_procedure_reports', []) or [])),
        ]
        for title, content in profile_sections:
            if content:
                sections.append({'title': title, 'content': content})
    
    # From assessment_data snapshot
    try:
        assessment_snapshot = record.assessment_data or {}
        if isinstance(assessment_snapshot, dict):
            excluded = {"discharge_checklist_summary", "patient_education_record"}
            known_sections = {
                "nursing_intake_assessment", "graphic_flow_sheets", "medication_administration_records",
                "history_physical_forms", "progress_notes", "provider_order_sheets", "operative_procedure_reports"
            }
            for k, v in assessment_snapshot.items():
                if k in excluded or k in known_sections:
                    continue
                sections.append({'title': k.replace('_', ' ').title(), 'content': v})
    except Exception:
        pass
        
    return {
        'patient_info': patient_info,
        'assessment_context': assessment_context,
        'sections': sections,
        # Legacy mappings for safety
        'medical_history': [], 
        'test_results': [],
        'treatment_timeline': []
    }


def generate_archive_pdf(record: PatientAssessmentArchive) -> bytes:
    """
    Build a PDF for an archived record using standardized analytics PDF format
    with proper styling, header, and footer matching the analytics template.
    """
    if not PLATYPUS_AVAILABLE:
        # Fallback to basic canvas if platypus not available
        return _generate_archive_pdf_basic(record)
    
    buffer = io.BytesIO()
    user = getattr(record, 'user', None)
    
    # Get hospital information using analytics format
    hospital_info = _get_archive_hospital_information(user, record)
    
    # Get user information for header
    user_info = _get_archive_user_information(user, record)
    
    # Prepare data for template
    pdf_data = _map_archive_to_pdf_data(record)
    
    # Generate PDF using class-based template
    template = PatientArchivePDF(buffer, hospital_info, user_info)
    template.generate(pdf_data)
    
    return buffer.getvalue()


def _generate_archive_pdf_basic(record: PatientAssessmentArchive) -> bytes:
    """
    Fallback basic PDF generation when platypus is not available
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    user = getattr(record, 'user', None)
    profile = getattr(record, 'patient_profile', None)

    # Header
    y = height - 1 * inch
    c.setFont("Helvetica-Bold", 16)
    hospital_name = (record.hospital_name or (getattr(user, 'hospital_name', '') or '')).strip() or "Hospital"
    c.drawString(1 * inch, y, hospital_name)
    y -= 16
    c.setFont("Helvetica", 11)
    hospital_addr = str(getattr(user, 'hospital_address', '') or '').strip()
    if hospital_addr:
        y = _draw_wrapped(c, hospital_addr, 1 * inch, y, width - 2 * inch)
    else:
        c.drawString(1 * inch, y, "Address: --")
        y -= 14

    # Patient demographics
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "Patient Demographics")
    y -= 14
    c.setFont("Helvetica", 11)
    full_name = getattr(user, 'full_name', '') or ''
    dob = getattr(user, 'date_of_birth', None)
    dob_str = dob.strftime('%Y-%m-%d') if dob else ''
    gender = getattr(user, 'gender', '') or ''
    blood = getattr(profile, 'blood_type', '') or ''
    c.drawString(1 * inch, y, f"Name: {full_name}")
    y -= 14
    c.drawString(1 * inch, y, f"DOB: {dob_str}")
    y -= 14
    c.drawString(1 * inch, y, f"Gender: {gender}")
    y -= 14
    if blood:
        c.drawString(1 * inch, y, f"Blood Type: {blood}")
        y -= 14
    # Context
    c.drawString(1 * inch, y, f"Assessment Type: {record.assessment_type}")
    y -= 14
    c.drawString(1 * inch, y, f"Medical Condition: {record.medical_condition}")
    y -= 14
    if record.last_assessed_at:
        c.drawString(1 * inch, y, f"Last Assessed: {record.last_assessed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        y -= 14
    c.drawString(1 * inch, y, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    y -= 20

    # Forms to include (exclude discharge and patient education)
    forms: List[tuple[str, Any]] = []
    if profile:
        forms.append(("Nursing Intake & Assessment", getattr(profile, 'nursing_intake_assessment', {}) or {}))
        forms.append(("Graphic Flow Sheets", list(getattr(profile, 'graphic_flow_sheets', []) or [])))
        forms.append(("Medication Administration Records", list(getattr(profile, 'medication_administration_records', []) or [])))
        forms.append(("History & Physical Forms", list(getattr(profile, 'history_physical_forms', []) or [])))
        forms.append(("Progress Notes", list(getattr(profile, 'progress_notes', []) or [])))
        forms.append(("Provider Order Sheets", list(getattr(profile, 'provider_order_sheets', []) or [])))
        forms.append(("Operative/Procedure Reports", list(getattr(profile, 'operative_procedure_reports', []) or [])))

    # Fallback: include any assessment data captured at archive time
    try:
        assessment_snapshot = record.decrypt_payload() or {}
    except Exception:
        assessment_snapshot = {}

    # Draw each section
    for title, data in forms:
        y = _draw_section_json(c, title, data, width, y)
        if y < 1 * inch:
            c.showPage()
            y = height - 1 * inch

    # If assessment snapshot has extra content, include sans the excluded sections
    if isinstance(assessment_snapshot, dict):
        excluded = {"discharge_checklist_summary", "patient_education_record"}
        for k, v in assessment_snapshot.items():
            if k in excluded:
                continue
            # Avoid repeating sections we already printed
            known_sections = {
                "nursing_intake_assessment", "graphic_flow_sheets", "medication_administration_records",
                "history_physical_forms", "progress_notes", "provider_order_sheets", "operative_procedure_reports"
            }
            if k in known_sections:
                continue
            y = _draw_section_json(c, f"{k}", v, width, y)
            if y < 1 * inch:
                c.showPage()
                y = height - 1 * inch

    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_medical_certificate_pdf(payload: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    issued_at = payload.get("issued_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    if PLATYPUS_AVAILABLE:
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="LetterheadTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=4, alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="LetterheadMeta", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#555555"), alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="DocTitle", parent=styles["Heading2"], fontSize=14, spaceAfter=10, alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="Label", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#2c3e50")))
        styles.add(ParagraphStyle(name="Body", parent=styles["Normal"], fontSize=11, leading=14, alignment=TA_JUSTIFY))
        styles.add(ParagraphStyle(name="Footer", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#7f8c8d"), alignment=TA_CENTER))

        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.75 * inch, leftMargin=0.75 * inch, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        story: List[Any] = []

        hospital_name = str(payload.get("hospital_name") or "Medical Facility")
        hospital_address = str(payload.get("hospital_address") or "")
        hospital_contact = str(payload.get("hospital_contact") or "")

        story.append(Paragraph(hospital_name, styles["LetterheadTitle"]))
        if hospital_address:
            story.append(Paragraph(hospital_address, styles["LetterheadMeta"]))
        if hospital_contact:
            story.append(Paragraph(hospital_contact, styles["LetterheadMeta"]))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, lineCap="round", color=colors.HexColor("#bdc3c7")))
        story.append(Spacer(1, 12))

        story.append(Paragraph("MEDICAL CERTIFICATE", styles["DocTitle"]))

        certificate_number = str(payload.get("certificate_number") or "")
        consultation_date = str(payload.get("consultation_date") or "")
        patient_name = str(payload.get("patient_name") or "")
        patient_dob = str(payload.get("patient_dob") or "")
        patient_age = str(payload.get("patient_age") or "")
        patient_gender = str(payload.get("patient_gender") or "")
        diagnosis = str(payload.get("diagnosis") or "")
        diagnoses_raw = payload.get("diagnoses")
        diagnoses: list[str] = []
        if isinstance(diagnoses_raw, list):
            diagnoses = [str(x).strip() for x in diagnoses_raw if str(x).strip()]
        hpi = str(payload.get("history_of_present_illness") or "")
        follow_up = str(payload.get("follow_up_instructions") or "")
        additional_notes = str(payload.get("additional_notes") or "")
        leave_start = str(payload.get("leave_start_date") or "")
        leave_end = str(payload.get("leave_end_date") or "")
        leave_days = str(payload.get("leave_days") or "")
        doctor_name = str(payload.get("doctor_name") or "")
        doctor_license = str(payload.get("doctor_license_number") or "")

        info_rows = [
            ["Certificate No.", certificate_number, "Consultation Date", consultation_date],
            ["Patient Name", patient_name, "Date of Birth", patient_dob],
            ["Age / Sex", f"{patient_age} / {patient_gender}".strip(" /"), "", ""],
        ]
        table = Table(info_rows, colWidths=[1.3 * inch, 2.4 * inch, 1.5 * inch, 2.1 * inch])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdcdc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        body_parts = []
        if diagnoses:
            try:
                from xml.sax.saxutils import escape as _xml_escape
            except Exception:
                def _xml_escape(v: str) -> str:  # type: ignore[misc]
                    return v
            diag_lines = "<br/>".join([f"&bull; {_xml_escape(d)}" for d in diagnoses])
            body_parts.append(f"Diagnoses/Impression:<br/>{diag_lines}.")
        elif diagnosis:
            body_parts.append(f"Diagnosis/Impression: <b>{diagnosis}</b>.")
        if leave_start and leave_end:
            leave_clause = f"The patient is advised to take sick leave from <b>{leave_start}</b> to <b>{leave_end}</b>"
            if leave_days:
                leave_clause += f" ({leave_days} day(s))"
            leave_clause += "."
            body_parts.append(leave_clause)
        body_parts.append("This certificate is issued upon request for sick leave entitlement purposes.")
        story.append(Paragraph(" ".join(body_parts), styles["Body"]))
        if hpi:
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"<b>Present Illness History:</b> {hpi}", styles["Body"]))
        if follow_up:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Follow-up Instructions:</b> {follow_up}", styles["Body"]))
        if additional_notes:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Additional Notes:</b> {additional_notes}", styles["Body"]))
        story.append(Spacer(1, 18))

        sign_table = Table(
            [
                ["", ""],
                ["", doctor_name],
                ["", f"License No.: {doctor_license}" if doctor_license else ""],
            ],
            colWidths=[4.2 * inch, 3.1 * inch],
        )
        sign_table.setStyle(TableStyle([
            ("ALIGN", (1, 1), (1, 2), "CENTER"),
            ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
            ("FONTNAME", (1, 2), (1, 2), "Helvetica"),
            ("FONTSIZE", (1, 1), (1, 2), 10),
        ]))
        story.append(sign_table)
        story.append(Spacer(1, 18))

        footer_text = f'This is a system-generated medical certificate authenticated by {doctor_name} on {issued_at}.'
        story.append(HRFlowable(width="100%", thickness=1, lineCap="round", color=colors.HexColor("#ecf0f1")))
        story.append(Spacer(1, 6))
        story.append(Paragraph(footer_text, styles["Footer"]))

        doc.build(story)
        return buffer.getvalue()

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 0.9 * inch
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, str(payload.get("hospital_name") or "Medical Facility"))
    y -= 14
    c.setFont("Helvetica", 9)
    hosp_addr = str(payload.get("hospital_address") or "")
    if hosp_addr:
        c.drawCentredString(width / 2, y, hosp_addr)
        y -= 12
    c.setFont("Helvetica-Bold", 14)
    y -= 18
    c.drawCentredString(width / 2, y, "MEDICAL CERTIFICATE")
    y -= 24
    c.setFont("Helvetica", 11)
    for label, val in [
        ("Certificate No.", payload.get("certificate_number")),
        ("Consultation Date", payload.get("consultation_date")),
        ("Patient Name", payload.get("patient_name")),
        ("Date of Birth", payload.get("patient_dob")),
        ("Age / Sex", f"{payload.get('patient_age') or ''} / {payload.get('patient_gender') or ''}".strip(" /")),
        ("Diagnosis", payload.get("diagnosis") if not isinstance(payload.get("diagnoses"), list) else "; ".join([str(x).strip() for x in (payload.get("diagnoses") or []) if str(x).strip()])),
        ("Sick Leave", f"{payload.get('leave_start_date') or ''} to {payload.get('leave_end_date') or ''}"),
    ]:
        if val is None:
            continue
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1 * inch, y, f"{label}:")
        c.setFont("Helvetica", 11)
        y = _draw_wrapped(c, str(val), 2.2 * inch, y, width - 3.2 * inch)
        y -= 6
    hpi = str(payload.get("history_of_present_illness") or "").strip()
    follow_up = str(payload.get("follow_up_instructions") or "").strip()
    additional_notes = str(payload.get("additional_notes") or "").strip()
    if hpi:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1 * inch, y, "Present Illness History:")
        c.setFont("Helvetica", 11)
        y = _draw_wrapped(c, hpi, 1 * inch, y - 14, width - 2 * inch)
        y -= 6
    if follow_up:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1 * inch, y, "Follow-up Instructions:")
        c.setFont("Helvetica", 11)
        y = _draw_wrapped(c, follow_up, 1 * inch, y - 14, width - 2 * inch)
        y -= 6
    if additional_notes:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1 * inch, y, "Additional Notes:")
        c.setFont("Helvetica", 11)
        y = _draw_wrapped(c, additional_notes, 1 * inch, y - 14, width - 2 * inch)
        y -= 6
    y -= 16
    doctor_name = str(payload.get("doctor_name") or "")
    doctor_license = str(payload.get("doctor_license_number") or "")
    c.setFont("Helvetica", 11)
    c.drawRightString(width - 1 * inch, y, doctor_name)
    y -= 14
    if doctor_license:
        c.drawRightString(width - 1 * inch, y, f"License No.: {doctor_license}")
        y -= 14
    y = 0.8 * inch
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, y, f"This is a system-generated medical certificate authenticated by {doctor_name} on {issued_at}.")
    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_prescription_pdf(payload: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    issued_at = payload.get("issued_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    meds = payload.get("medications") or []
    if not isinstance(meds, list):
        meds = []

    if PLATYPUS_AVAILABLE:
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="LetterheadTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=4, alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="LetterheadMeta", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#555555"), alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="DocTitle", parent=styles["Heading2"], fontSize=14, spaceAfter=10, alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="Footer", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#7f8c8d"), alignment=TA_CENTER))

        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.75 * inch, leftMargin=0.75 * inch, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        story: List[Any] = []

        hospital_name = str(payload.get("hospital_name") or "Medical Facility")
        hospital_address = str(payload.get("hospital_address") or "")
        hospital_contact = str(payload.get("hospital_contact") or "")

        story.append(Paragraph(hospital_name, styles["LetterheadTitle"]))
        if hospital_address:
            story.append(Paragraph(hospital_address, styles["LetterheadMeta"]))
        if hospital_contact:
            story.append(Paragraph(hospital_contact, styles["LetterheadMeta"]))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, lineCap="round", color=colors.HexColor("#bdc3c7")))
        story.append(Spacer(1, 12))

        story.append(Paragraph("PRESCRIPTION", styles["DocTitle"]))

        prescription_number = str(payload.get("prescription_number") or "")
        consultation_date = str(payload.get("consultation_date") or "")
        patient_name = str(payload.get("patient_name") or "")
        patient_id = str(payload.get("patient_id") or "")
        patient_dob = str(payload.get("patient_dob") or "")
        patient_age = str(payload.get("patient_age") or "")
        patient_gender = str(payload.get("patient_gender") or "")
        doctor_name = str(payload.get("doctor_name") or "")
        doctor_license = str(payload.get("doctor_license_number") or "")

        info_rows = [
            ["Prescription No.", prescription_number, "Consultation Date", consultation_date],
            ["Patient Name", patient_name, "Patient ID", patient_id],
            ["Date of Birth", patient_dob, "Age / Sex", f"{patient_age} / {patient_gender}".strip(" /")],
        ]
        table = Table(info_rows, colWidths=[1.4 * inch, 2.3 * inch, 1.5 * inch, 2.1 * inch])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdcdc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        med_header = ["Drug Name", "Dosage", "Frequency", "Duration", "Instructions"]
        med_rows = [med_header]
        for m in meds:
            if not isinstance(m, dict):
                continue
            med_rows.append([
                str(m.get("drug_name") or ""),
                str(m.get("dosage") or ""),
                str(m.get("frequency") or ""),
                str(m.get("duration") or ""),
                str(m.get("instructions") or ""),
            ])

        if len(med_rows) == 1:
            med_rows.append(["", "", "", "", ""])

        med_table = Table(med_rows, colWidths=[1.7 * inch, 1.0 * inch, 1.1 * inch, 1.0 * inch, 1.7 * inch])
        med_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf0f1")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdcdc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        story.append(med_table)
        story.append(Spacer(1, 16))

        sign_table = Table(
            [
                ["", ""],
                ["", doctor_name],
                ["", f"License No.: {doctor_license}" if doctor_license else ""],
            ],
            colWidths=[4.2 * inch, 3.1 * inch],
        )
        sign_table.setStyle(TableStyle([
            ("LINEABOVE", (1, 1), (1, 1), 1, colors.HexColor("#2c3e50")),
            ("ALIGN", (1, 1), (1, 2), "CENTER"),
            ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
            ("FONTNAME", (1, 2), (1, 2), "Helvetica"),
            ("FONTSIZE", (1, 1), (1, 2), 10),
        ]))
        story.append(sign_table)
        story.append(Spacer(1, 18))

        footer_text = f'This is a system-generated prescription authenticated by {doctor_name} on {issued_at}.'
        story.append(HRFlowable(width="100%", thickness=1, lineCap="round", color=colors.HexColor("#ecf0f1")))
        story.append(Spacer(1, 6))
        story.append(Paragraph(footer_text, styles["Footer"]))

        doc.build(story)
        return buffer.getvalue()

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 0.9 * inch
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, str(payload.get("hospital_name") or "Medical Facility"))
    y -= 14
    c.setFont("Helvetica", 9)
    hosp_addr = str(payload.get("hospital_address") or "")
    if hosp_addr:
        c.drawCentredString(width / 2, y, hosp_addr)
        y -= 12
    c.setFont("Helvetica-Bold", 14)
    y -= 18
    c.drawCentredString(width / 2, y, "PRESCRIPTION")
    y -= 24
    c.setFont("Helvetica", 11)
    for label, val in [
        ("Prescription No.", payload.get("prescription_number")),
        ("Consultation Date", payload.get("consultation_date")),
        ("Patient Name", payload.get("patient_name")),
        ("Patient ID", payload.get("patient_id")),
    ]:
        if val is None:
            continue
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1 * inch, y, f"{label}:")
        c.setFont("Helvetica", 11)
        y = _draw_wrapped(c, str(val), 2.5 * inch, y, width - 3.5 * inch)
        y -= 6
    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y, "Medications:")
    y -= 14
    c.setFont("Helvetica", 10)
    for i, m in enumerate(meds, 1):
        if not isinstance(m, dict):
            continue
        line = f"{i}. {m.get('drug_name') or ''} | {m.get('dosage') or ''} | {m.get('frequency') or ''} | {m.get('duration') or ''} | {m.get('instructions') or ''}"
        y = _draw_wrapped(c, line, 1 * inch, y, width - 2 * inch, font_size=10)
        y -= 4
        if y < 1.2 * inch:
            c.showPage()
            y = height - 1 * inch
    doctor_name = str(payload.get("doctor_name") or "")
    y = 1.1 * inch
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, y, f"This is a system-generated prescription authenticated by {doctor_name} on {issued_at}.")
    c.showPage()
    c.save()
    return buffer.getvalue()
