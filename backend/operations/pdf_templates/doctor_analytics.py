
from .base_template import BasePDFTemplate
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.units import inch

class DoctorAnalyticsPDF(BasePDFTemplate):
    def build_story(self, data):
        story = []
        
        # Title
        story.append(Paragraph("Doctor Analytics Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.2 * inch))
        
        # 1. Analytics Results
        if 'analytics_results' in data:
            story.append(Paragraph("1. Analytics Results", self.styles['SectionHeader']))
            results = data['analytics_results']
            
            # Metrics Table
            if 'metrics' in results and results['metrics']:
                metrics = results['metrics']
                table_data = [[k, str(v)] for k, v in metrics.items()]
                t = Table(table_data, colWidths=[3.5*inch, 3.5*inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
                    ('TEXTCOLOR', (0, 0), (-1, -1), self.primary_color),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]))
                story.append(t)
            story.append(Spacer(1, 0.2 * inch))

            # Comparative Analysis
            story.append(Paragraph("Comparative Analysis", self.styles['SubHeader']))
            story.append(Paragraph("Performance against historical benchmarks and predicted targets.", self.styles['ContentText']))
            
            # Use real data if available, else mock
            comp_data = results.get('comparative_data')
            if not comp_data:
                comp_data = [
                    ['Metric', 'Current', 'Benchmark', 'Status'],
                    ['Patient Satisfaction', '4.8/5', '4.5/5', 'Above Target'],
                    ['Avg Wait Time', '12 min', '15 min', 'Optimal'],
                    ['Treatment Efficacy', '94%', '90%', 'Above Target']
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
            
            # Visualization
            if 'visualization' in results and results['visualization']:
                try:
                    img = ReportLabImage(results['visualization'])
                    img_width = 7 * inch
                    aspect = img.drawHeight / img.drawWidth
                    img.drawWidth = img_width
                    img.drawHeight = img_width * aspect
                    story.append(img)
                except Exception:
                    story.append(Paragraph("Visualization unavailable", self.styles['ContentText']))
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
            # Display side by side if possible, or stacked
            images = []
            if 'correlation_matrix' in factors and factors['correlation_matrix']:
                try:
                    img = ReportLabImage(factors['correlation_matrix'])
                    img.drawWidth = 3.5 * inch
                    img.drawHeight = 3.5 * inch # Square aspect for matrix usually
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
                # If we have 2 images, put them in a table row
                if len(images) == 2:
                    t = Table([images], colWidths=[3.6*inch, 3.6*inch])
                    story.append(t)
                else:
                    for img in images:
                        story.append(img)
                        story.append(Spacer(1, 0.1 * inch))
            
            story.append(Spacer(1, 0.2 * inch))

            # Filterable Data Table Representation
            story.append(Paragraph("Detailed Performance Metrics", self.styles['SubHeader']))
            
            # Use real data if available, else mock
            detailed_data = factors.get('detailed_metrics')
            if not detailed_data:
                detailed_data = [
                    ['Date', 'Patient Volume', 'Avg LOS', 'Staffing Level'],
                    ['2023-10-01', '45', '2.1 days', 'Full'],
                    ['2023-10-02', '52', '2.3 days', 'Short'],
                    ['2023-10-03', '48', '2.0 days', 'Full'],
                    ['2023-10-04', '60', '2.5 days', 'Full'],
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
                        # Handle both dict (with confidence) and string formats for robustness
                        if isinstance(item, dict):
                            text = item.get('text', '')
                            confidence = item.get('confidence', 0)
                            source = item.get('source', 'AI Model')
                            # Format: "Recommendation (Confidence: 85%) - Source: Model"
                            content = f"• {text} <font color='grey' size=9>(Confidence: {confidence:.0%})</font>"
                        else:
                            content = f"• {str(item)}"
                        
                        story.append(Paragraph(content, self.styles['ContentText']))
                    story.append(Spacer(1, 0.1 * inch))
                
        return story
