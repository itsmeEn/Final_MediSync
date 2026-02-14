
from .base_template import BasePDFTemplate
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.units import inch

class NurseAnalyticsPDF(BasePDFTemplate):
    def build_story(self, data):
        story = []
        
        # Title
        story.append(Paragraph("Nurse Analytics Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.2 * inch))
        
        # 1. Analytics Results
        if 'analytics_results' in data:
            story.append(Paragraph("1. Analytics Results", self.styles['SectionHeader']))
            results = data['analytics_results']
            
            # Metrics Table
            if 'metrics' in results and results['metrics']:
                metrics = results['metrics']
                table_data = [[k, str(v)] for k, v in metrics.items()]
                
                # Use available width (approx 7.2 inch)
                col_width = 3.5 * inch
                t = Table(table_data, colWidths=[col_width, col_width])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.aliceblue), # First col background
                    ('TEXTCOLOR', (0, 0), (-1, -1), self.primary_color),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Key aligned left
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'), # Value aligned right
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                story.append(t)
            story.append(Spacer(1, 0.3 * inch))

            # Visualization
            if 'visualization' in results and results['visualization']:
                try:
                    img = ReportLabImage(results['visualization'])
                    # Scale to fit width (max 7 inch)
                    max_width = 7 * inch
                    img_width = max_width
                    aspect = img.drawHeight / img.drawWidth
                    img.drawWidth = img_width
                    img.drawHeight = img_width * aspect
                    story.append(img)
                except Exception:
                    story.append(Paragraph("Visualization unavailable", self.styles['ContentText']))
            story.append(Spacer(1, 0.3 * inch))

            # Comparative Analysis (Nurse Specific)
            story.append(Paragraph("Comparative Analysis", self.styles['SubHeader']))
            story.append(Paragraph("Performance metrics against department standards.", self.styles['ContentText']))
            
            # Use real data if available, else mock
            comp_data = results.get('comparative_data')
            if not comp_data:
                comp_data = [
                    ['Metric', 'Current', 'Target', 'Status'],
                    ['Medication Accuracy', '99.8%', '99.9%', 'On Track'],
                    ['Patient Response', '3.5 min', '5.0 min', 'Excellent'],
                    ['Shift Coverage', '100%', '100%', 'Optimal']
                ]
            
            t_comp = Table(comp_data, colWidths=[2.0*inch, 1.5*inch, 1.5*inch, 2.0*inch])
            t_comp.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]))
            story.append(t_comp)
            story.append(Spacer(1, 0.3 * inch))

            # Medication Records (if available)
            if 'medication_records' in results and results['medication_records']:
                story.append(Paragraph("Medication Administration Summary", self.styles['SubHeader']))
                med_records = results['medication_records']
                if isinstance(med_records, dict):
                    table_data = [[k, str(v)] for k, v in med_records.items()]
                    # 4 columns logic if list, or 2 cols if dict
                    t = Table(table_data, colWidths=[3.5*inch, 3.5*inch])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
                        ('TEXTCOLOR', (0, 0), (-1, -1), self.primary_color),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ]))
                    story.append(t)
                story.append(Spacer(1, 0.3 * inch))

        # 2. Factors Affecting Performance
        if 'performance_factors' in data:
            story.append(Paragraph("2. Factors Affecting Performance", self.styles['SectionHeader']))
            factors = data['performance_factors']
            
            # Significant Factors List
            if 'significant_factors' in factors and factors['significant_factors']:
                story.append(Paragraph("Significant Factors:", self.styles['SubHeader']))
                for factor in factors['significant_factors']:
                    story.append(Paragraph(f"• {factor}", self.styles['ContentText']))
                story.append(Spacer(1, 0.2 * inch))

            # Visualizations (Correlation & Trends)
            images = []
            if 'correlation_matrix' in factors and factors['correlation_matrix']:
                try:
                    img = ReportLabImage(factors['correlation_matrix'])
                    img.drawWidth = 3.5 * inch
                    img.drawHeight = 3.5 * inch
                    images.append(img)
                except Exception:
                    pass
            
            if 'trend_analysis' in factors and factors['trend_analysis']:
                try:
                    img = ReportLabImage(factors['trend_analysis'])
                    img.drawWidth = 3.5 * inch
                    img.drawHeight = 2.5 * inch
                    images.append(img)
                except Exception:
                    pass
            
            if images:
                if len(images) == 2:
                    t = Table([images], colWidths=[3.6*inch, 3.6*inch])
                    story.append(t)
                else:
                    for img in images:
                        story.append(img)
                        story.append(Spacer(1, 0.1 * inch))
            
            story.append(Spacer(1, 0.2 * inch))

            # Detailed Performance Table (Nurse Specific)
            story.append(Paragraph("Detailed Shift Metrics", self.styles['SubHeader']))
            
            # Use real data if available, else mock
            detailed_data = factors.get('detailed_metrics')
            if not detailed_data:
                detailed_data = [
                    ['Date', 'Shift', 'Patients', 'Meds Admin'],
                    ['2023-10-01', 'Morning', '12', '45'],
                    ['2023-10-02', 'Night', '15', '52'],
                    ['2023-10-03', 'Morning', '10', '38'],
                    ['2023-10-04', 'Evening', '14', '48'],
                ]
            
            t_detail = Table(detailed_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.6*inch])
            t_detail.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(t_detail)
            story.append(Spacer(1, 0.3 * inch))

        # 3. AI Recommendation Engine
        if 'ai_recommendations' in data:
            story.append(Paragraph("3. AI Recommendation Engine", self.styles['SectionHeader']))
            recs = data['ai_recommendations']
            
            categories = {
                'actionable': 'Actionable Insights',
                'predictive': 'Predictive Suggestions',
                'strategies': 'Performance Strategies',
                'resource': 'Resource Advice'
            }
            
            for key, title in categories.items():
                if key in recs and recs[key]:
                    story.append(Paragraph(title, self.styles['SubHeader']))
                    for item in recs[key]:
                        if isinstance(item, dict):
                            text = item.get('text', '')
                            confidence = item.get('confidence', 0)
                            # Format: "Recommendation (Confidence: 85%)"
                            content = f"• {text} <font color='grey' size=9>(Confidence: {confidence:.0%})</font>"
                        else:
                            content = f"• {str(item)}"
                        
                        story.append(Paragraph(content, self.styles['ContentText']))
                    story.append(Spacer(1, 0.1 * inch))

        return story
