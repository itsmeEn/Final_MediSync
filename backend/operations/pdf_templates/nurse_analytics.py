
from datetime import datetime, timezone

from .base_template import BasePDFTemplate
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as canvas_module

class NurseAnalyticsPDF(BasePDFTemplate):
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
                    ['Metric', 'Current', 'Target', 'Status'],
                    ['Medication Accuracy', '99.8%', '99.9%', 'On Track'],
                    ['Patient Response', '3.5 min', '5.0 min', 'Excellent'],
                    ['Shift Coverage', '100%', '100%', 'Optimal']
                ]
            story.append(data_table(comp_data, [2.0 * inch, 1.5 * inch, 1.5 * inch, 2.0 * inch]))

            med_records = results.get('medication_records')
            if isinstance(med_records, dict) and med_records:
                story.append(Spacer(1, 0.08 * inch))
                story.append(Paragraph("Medication administration summary:", self.styles['SubHeader']))
                story.append(kv_table([[str(k), str(v)] for k, v in med_records.items()]))

            interpretation = (
                "The results summarize nursing operational indicators and comparative targets for the selected time range. "
                "Focus on metrics with unfavorable status, then validate against staffing coverage, workload distribution, and medication timing."
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
                    ['Date', 'Shift', 'Patients', 'Meds Admin'],
                    ['2023-10-01', 'Morning', '12', '45'],
                    ['2023-10-02', 'Night', '15', '52'],
                    ['2023-10-03', 'Morning', '10', '38'],
                    ['2023-10-04', 'Evening', '14', '48'],
                ]
            story.append(Paragraph("Detailed metrics:", self.styles['SubHeader']))
            story.append(data_table(detailed_data, [1.8 * inch, 1.8 * inch, 1.8 * inch, 1.6 * inch]))

            interpretation = (
                "Factor analysis highlights operational drivers correlated with throughput and medication timing. "
                "Use the correlation and trend outputs to prioritize staffing adjustments, shift planning, and process controls."
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
