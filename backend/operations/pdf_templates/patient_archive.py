
from .base_template import BasePDFTemplate
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

class PatientArchivePDF(BasePDFTemplate):
    def build_story(self, data):
        story = []
        
        # Title
        story.append(Paragraph("Patient Archive Document", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Patient Details Header
        if 'patient_info' in data:
            self._add_patient_info(story, data['patient_info'])

        # Assessment Context
        if 'assessment_context' in data:
            self._add_assessment_context(story, data['assessment_context'])

        # 1. Comprehensive Medical History (Legacy/Specific)
        if 'medical_history' in data:
            story.append(Paragraph("Medical History", self.styles['SectionHeader']))
            history = data['medical_history']
            if history:
                for item in history:
                    text = f"<b>Date:</b> {item.get('date', '')} - <b>Condition:</b> {item.get('condition', '')}<br/>" \
                           f"<i>Notes:</i> {item.get('notes', '')}"
                    story.append(Paragraph(text, self.styles['ContentText']))
                    story.append(Spacer(1, 0.1 * inch))
            else:
                story.append(Paragraph("No medical history recorded.", self.styles['ContentText']))
            story.append(Spacer(1, 0.2 * inch))

        # 2. Test Results (Legacy/Specific)
        if 'test_results' in data:
            story.append(Paragraph("Test Results", self.styles['SectionHeader']))
            results = data['test_results']
            if results:
                table_data = [['Date', 'Test Name', 'Result', 'Ref Range']]
                for r in results:
                    table_data.append([
                        r.get('date', ''),
                        r.get('name', ''),
                        r.get('result', ''),
                        r.get('range', '')
                    ])
                
                t = Table(table_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(t)
            else:
                story.append(Paragraph("No test results available.", self.styles['ContentText']))
            story.append(Spacer(1, 0.2 * inch))

        # 3. Treatment Timeline (Legacy/Specific)
        if 'treatment_timeline' in data:
            story.append(Paragraph("Treatment Timeline", self.styles['SectionHeader']))
            timeline = data['treatment_timeline']
            if timeline:
                for event in timeline:
                    story.append(Paragraph(f"• <b>{event.get('date', '')}</b>: {event.get('event', '')}", self.styles['ContentText']))
            else:
                story.append(Paragraph("No treatment events recorded.", self.styles['ContentText']))
            story.append(Spacer(1, 0.2 * inch))

        # 4. Dynamic Sections (Forms, etc.)
        if 'sections' in data:
            for section in data['sections']:
                self._add_section(story, section)

        return story

    def _add_patient_info(self, story, p_info):
        story.append(Paragraph("Patient Demographics", self.styles['SubHeader']))
        
        # Convert dict to table data
        table_data = []
        mapping = {
            'name': 'Patient Name',
            'id': 'Patient ID',
            'dob': 'Date of Birth',
            'gender': 'Gender',
            'blood_group': 'Blood Type'
        }
        
        for key, label in mapping.items():
            if key in p_info:
                table_data.append([label + ":", str(p_info[key])])
        
        # Add any other keys not in mapping
        for k, v in p_info.items():
            if k not in mapping:
                formatted_key = k.replace('_', ' ').title() + ":"
                table_data.append([formatted_key, str(v)])

        if table_data:
            t = Table(table_data, colWidths=[2*inch, 4*inch])
            t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    def _add_assessment_context(self, story, context):
        story.append(Paragraph("Assessment Context", self.styles['SubHeader']))
        table_data = []
        for k, v in context.items():
            formatted_key = k.replace('_', ' ').title() + ":"
            table_data.append([formatted_key, str(v)])
            
        if table_data:
            t = Table(table_data, colWidths=[2*inch, 4*inch])
            t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    def _add_section(self, story, section):
        title = section.get('title', 'Untitled Section')
        content = section.get('content')
        
        story.append(Paragraph(title, self.styles['SectionHeader']))
        
        if not content:
            story.append(Paragraph("No data available", self.styles['ContentText']))
        elif isinstance(content, dict):
            self._render_dict(story, content)
        elif isinstance(content, list):
            self._render_list(story, content)
        else:
            story.append(Paragraph(str(content), self.styles['ContentText']))
        
        story.append(Spacer(1, 0.15 * inch))

    def _render_dict(self, story, data):
        table_data = []
        for key, value in data.items():
            formatted_key = key.replace('_', ' ').title()
            if isinstance(value, (dict, list)):
                formatted_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            else:
                formatted_value = str(value) if value is not None else "Not specified"
            table_data.append([formatted_key, formatted_value])
        
        if table_data:
            t = Table(table_data, colWidths=[2*inch, 4*inch])
            t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ecf0f1')),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(t)

    def _render_list(self, story, data):
        for i, item in enumerate(data, 1):
            story.append(Paragraph(f"Entry {i}:", self.styles['SubHeader']))
            if isinstance(item, dict):
                self._render_dict(story, item)
            else:
                story.append(Paragraph(str(item), self.styles['ContentText']))
            story.append(Spacer(1, 0.1 * inch))
