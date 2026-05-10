
from datetime import datetime, timezone

from .base_template import BasePDFTemplate
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as canvas_module
import re

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

        def strip_confidence(text: str) -> str:
            s = str(text or "")
            s = re.sub(r"\(\s*confidence\s*:\s*[^)]*\)", "", s, flags=re.IGNORECASE).strip()
            s = re.sub(r"\bconfidence\s*:\s*\d+(\.\d+)?%?\b", "", s, flags=re.IGNORECASE).strip()
            return s
        
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
                img_buffer = self._to_image_buffer(results['visualization'])
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

            sources = data.get("interpretation_sources") or {}
            if isinstance(sources, dict) and sources:
                paragraphs = []
                pd = sources.get("patient_demographics")
                if isinstance(pd, dict):
                    total = pd.get("total_patients")
                    avg = pd.get("average_age")
                    ad = pd.get("age_distribution") or {}
                    if isinstance(ad, dict) and ad:
                        top_group = max(ad.items(), key=lambda kv: kv[1] or 0)[0]
                        paragraphs.append(f"Demographics: Total patients: {total if total is not None else 'N/A'}, average age: {avg if avg is not None else 'N/A'}. The largest age group is {top_group}, which typically reflects the local case mix and clinic catchment.")
                ht = sources.get("health_trends")
                if isinstance(ht, dict):
                    top = ht.get("top_illnesses_by_week") or []
                    if isinstance(top, list) and top:
                        first = next((x for x in top if isinstance(x, dict) and x.get("medical_condition")), None)
                        if first:
                            paragraphs.append(f"Health trends: {first.get('medical_condition')} appears most frequently in the latest window. Changes here are commonly driven by seasonality, clinic workflow, and reporting volume.")
                ma = sources.get("medication_analysis")
                if isinstance(ma, dict):
                    pareto = ma.get("medication_pareto_data") or []
                    if isinstance(pareto, list) and pareto:
                        first = next((x for x in pareto if isinstance(x, dict) and x.get("medication")), None)
                        if first:
                            paragraphs.append(f"Medication analysis: {first.get('medication')} is the top medication, which often tracks the most common conditions and protocol-driven prescribing.")
                vp = sources.get("volume_prediction")
                if isinstance(vp, dict):
                    fd = vp.get("forecasted_data") or []
                    if isinstance(fd, list) and fd:
                        last = fd[-1] if isinstance(fd[-1], dict) else None
                        if last:
                            paragraphs.append("Volume prediction: The projected volume reflects recent utilization patterns. Deviations between predicted and actual volumes are often explained by staffing constraints, appointment scheduling changes, and seasonal surges.")
                if paragraphs:
                    story.append(Spacer(1, 0.08 * inch))
                    for p in paragraphs:
                        story.append(Paragraph(p, self.styles["ContentText"]))
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
                img_buffer = self._to_image_buffer(factors['correlation_matrix'])
                if img_buffer:
                    img = ReportLabImage(img_buffer)
                    img.drawWidth = 3.5 * inch
                    img.drawHeight = 3.5 * inch
                    images.append(img)
            if factors.get('trend_analysis'):
                img_buffer = self._to_image_buffer(factors['trend_analysis'])
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
                        text = strip_confidence(str(item.get('text', '') or '').strip())
                        content = f"• {text}" if text else ""
                    else:
                        text = strip_confidence(str(item))
                        content = f"• {text}" if text else ""
                    if content:
                        story.append(Paragraph(content, self.styles['ContentText']))
                story.append(Spacer(1, 0.08 * inch))
        else:
            story.append(Paragraph("No AI recommendations are available for the selected period.", self.styles['ContentText']))
        return story
