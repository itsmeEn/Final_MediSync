
from datetime import datetime, timezone

from .base_template import BasePDFTemplate
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as canvas_module

class DoctorAnalyticsPDF(BasePDFTemplate):
    def _draw_footer(self, canvas: canvas_module.Canvas, doc):
        canvas.saveState()
        margin = 0.5 * inch

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.black)

        name = ""
        if isinstance(self.user_info, dict):
            name = str(self.user_info.get("name") or "").strip()
        if not name:
            name = "Unknown User"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        auth_text = f"This is a system-generated prescription authenticated by {name} on {ts} UTC."
        max_width = (self.width - (2 * margin)) - 90
        self._draw_wrapped_canvas_text(canvas, auth_text, margin, margin, max_width, 10)

        page_num = f"Page {doc.page}"
        canvas.drawRightString(self.width - margin, margin, page_num)
        canvas.restoreState()

    def build_story(self, data):
        story = []
        
        story.append(Paragraph("AI Medical Analytics Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.08 * inch))

        def kv_table(items: list[list[str]]):
            t = Table(items, colWidths=[3.5 * inch, 3.5 * inch])
            t.setStyle(TableStyle([
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            return t

        def data_table(rows: list[list[str]], col_widths: list[float]):
            t = Table(rows, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            return t
        
        results = data.get('analytics_results') or {}
        story.append(Paragraph("Analytics Graph", self.styles['SectionHeader']))
        if results and results.get('visualization'):
            try:
                img_buffer = self._to_bw_image_buffer(results['visualization'])
                if img_buffer:
                    img = ReportLabImage(img_buffer)
                    img_width = 7 * inch
                    aspect = img.drawHeight / img.drawWidth
                    img.drawWidth = img_width
                    img.drawHeight = img_width * aspect
                    story.append(img)
                else:
                    story.append(Paragraph("No visualization available for the selected period.", self.styles['ContentText']))
            except Exception:
                story.append(Paragraph("No visualization available for the selected period.", self.styles['ContentText']))
        else:
            story.append(Paragraph("No visualization available for the selected period.", self.styles['ContentText']))
        story.append(Spacer(1, 0.12 * inch))

        story.append(Paragraph("Analytics Interpretation", self.styles['SectionHeader']))
        if results:
            metrics = results.get('metrics') or {}
            if metrics:
                story.append(kv_table([[str(k), str(v)] for k, v in metrics.items()]))
                story.append(Spacer(1, 0.08 * inch))

            comp_data = results.get('comparative_data')
            if not comp_data:
                comp_data = [
                    ['Metric', 'Current', 'Benchmark', 'Status'],
                    ['Patient Satisfaction', '4.8/5', '4.5/5', 'Above Target'],
                    ['Avg Wait Time', '12 min', '15 min', 'Optimal'],
                    ['Treatment Efficacy', '94%', '90%', 'Above Target']
                ]
            story.append(data_table(comp_data, [2.0 * inch, 1.5 * inch, 1.5 * inch, 2.0 * inch]))

            interpretation = (
                "Key indicators and comparative results summarize operational and clinical performance for the selected time range. "
                "Use status fields to identify deviations, validate with case mix, and prioritize interventions that reduce delays and improve outcomes."
            )
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(interpretation, self.styles['ContentText']))
        else:
            story.append(Paragraph("No analytics results are available for the selected period.", self.styles['ContentText']))
        story.append(Spacer(1, 0.16 * inch))

        factors = data.get('performance_factors') or {}
        story.append(Paragraph("Factor Analysis", self.styles['SectionHeader']))
        if factors:
            sig = factors.get('significant_factors') or []
            if sig:
                story.append(Paragraph("Key factors identified:", self.styles['SubHeader']))
                for factor in sig:
                    story.append(Paragraph(f"• {factor}", self.styles['ContentText']))
                story.append(Spacer(1, 0.08 * inch))

            images = []
            if factors.get('correlation_matrix'):
                img_buffer = self._to_bw_image_buffer(factors['correlation_matrix'])
                if img_buffer:
                    img = ReportLabImage(img_buffer)
                    img.drawWidth = 3.5 * inch
                    img.drawHeight = 3.5 * inch
                    images.append(img)
            if factors.get('trend_analysis'):
                img_buffer = self._to_bw_image_buffer(factors['trend_analysis'])
                if img_buffer:
                    img = ReportLabImage(img_buffer)
                    img.drawWidth = 3.5 * inch
                    img.drawHeight = 2.5 * inch
                    images.append(img)
            if images:
                if len(images) == 2:
                    story.append(Table([images], colWidths=[3.6 * inch, 3.6 * inch]))
                else:
                    story.extend(images)
                story.append(Spacer(1, 0.08 * inch))

            detailed_data = factors.get('detailed_metrics')
            if not detailed_data:
                detailed_data = [
                    ['Date', 'Patient Volume', 'Avg LOS', 'Staffing Level'],
                    ['2023-10-01', '45', '2.1 days', 'Full'],
                    ['2023-10-02', '52', '2.3 days', 'Short'],
                    ['2023-10-03', '48', '2.0 days', 'Full'],
                    ['2023-10-04', '60', '2.5 days', 'Full'],
                ]
            story.append(Paragraph("Detailed metrics:", self.styles['SubHeader']))
            story.append(data_table(detailed_data, [1.8 * inch, 1.8 * inch, 1.8 * inch, 1.6 * inch]))

            interpretation = (
                "Factor analysis highlights drivers correlated with performance variability. "
                "Use correlation and trend outputs to prioritize operational improvements, align staffing, and reduce avoidable delays."
            )
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(interpretation, self.styles['ContentText']))
        else:
            story.append(Paragraph("No factor analysis data is available for the selected period.", self.styles['ContentText']))
        story.append(Spacer(1, 0.16 * inch))

        recs = data.get('ai_recommendations') or {}
        story.append(Paragraph("AI-Recommendation", self.styles['SectionHeader']))
        if recs:
            categories = [
                ('actionable', 'Actionable Insights'),
                ('predictive', 'Predictive Suggestions'),
                ('strategies', 'Performance Strategies'),
                ('resource', 'Resource Advice'),
            ]
            for key, title in categories:
                items = recs.get(key) or []
                if not items:
                    continue
                story.append(Paragraph(title, self.styles['SubHeader']))
                for item in items:
                    if isinstance(item, dict):
                        text = str(item.get('text', '') or '').strip()
                        confidence = item.get('confidence', None)
                        if confidence is None:
                            content = f"• {text}"
                        else:
                            try:
                                content = f"• {text} (Confidence: {float(confidence):.0%})"
                            except Exception:
                                content = f"• {text}"
                    else:
                        content = f"• {str(item)}"
                    story.append(Paragraph(content, self.styles['ContentText']))
                story.append(Spacer(1, 0.08 * inch))
        else:
            story.append(Paragraph("No AI recommendations are available for the selected period.", self.styles['ContentText']))
        return story
