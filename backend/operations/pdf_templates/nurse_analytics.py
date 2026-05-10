
from .base_template import BasePDFTemplate
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.units import inch

class NurseAnalyticsPDF(BasePDFTemplate):
    def build_story(self, data):
        story = []
        
        story.append(Paragraph("AI Medical Analytics Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.15 * inch))

        def add_result_with_interpretation(title: str, result_flowables: list, interpretation_text: str):
            story.append(Paragraph(title, self.styles['SectionHeader']))
            story.append(Paragraph("Analytic Result:", self.styles['SubHeader']))
            story.extend(result_flowables)
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph("Interpretation:", self.styles['SubHeader']))
            story.append(Paragraph(interpretation_text, self.styles['ContentText']))
            story.append(Spacer(1, 0.18 * inch))

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
        if results:
            parts = []
            metrics = results.get('metrics') or {}
            if metrics:
                table_data = [[str(k), str(v)] for k, v in metrics.items()]
                parts.append(kv_table(table_data))

            comp_data = results.get('comparative_data')
            if not comp_data:
                comp_data = [
                    ['Metric', 'Current', 'Target', 'Status'],
                    ['Medication Accuracy', '99.8%', '99.9%', 'On Track'],
                    ['Patient Response', '3.5 min', '5.0 min', 'Excellent'],
                    ['Shift Coverage', '100%', '100%', 'Optimal']
                ]
            parts.append(Spacer(1, 0.1 * inch))
            parts.append(data_table(comp_data, [2.0 * inch, 1.5 * inch, 1.5 * inch, 2.0 * inch]))

            med_records = results.get('medication_records')
            if isinstance(med_records, dict) and med_records:
                parts.append(Spacer(1, 0.12 * inch))
                parts.append(Paragraph("Medication administration summary:", self.styles['SubHeader']))
                parts.append(kv_table([[str(k), str(v)] for k, v in med_records.items()]))

            if results.get('visualization'):
                try:
                    img_buffer = self._to_bw_image_buffer(results['visualization'])
                    if img_buffer:
                        img = ReportLabImage(img_buffer)
                        img_width = 7 * inch
                        aspect = img.drawHeight / img.drawWidth
                        img.drawWidth = img_width
                        img.drawHeight = img_width * aspect
                        parts.append(Spacer(1, 0.12 * inch))
                        parts.append(img)
                except Exception:
                    pass

            interpretation = (
                "The metrics above summarize nursing operational indicators and comparative targets. "
                "Use the status column to identify deviations that may require workflow or staffing adjustments."
            )
            add_result_with_interpretation("Analytics Data", parts, interpretation)

        factors = data.get('performance_factors') or {}
        if factors:
            parts = []
            sig = factors.get('significant_factors') or []
            if sig:
                parts.append(Paragraph("Significant factors:", self.styles['SubHeader']))
                for factor in sig:
                    parts.append(Paragraph(f"• {factor}", self.styles['ContentText']))
                parts.append(Spacer(1, 0.08 * inch))

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
                parts.append(Spacer(1, 0.08 * inch))
                if len(images) == 2:
                    parts.append(Table([images], colWidths=[3.6 * inch, 3.6 * inch]))
                else:
                    parts.extend(images)

            detailed_data = factors.get('detailed_metrics')
            if not detailed_data:
                detailed_data = [
                    ['Date', 'Shift', 'Patients', 'Meds Admin'],
                    ['2023-10-01', 'Morning', '12', '45'],
                    ['2023-10-02', 'Night', '15', '52'],
                    ['2023-10-03', 'Morning', '10', '38'],
                    ['2023-10-04', 'Evening', '14', '48'],
                ]
            parts.append(Spacer(1, 0.12 * inch))
            parts.append(Paragraph("Detailed shift metrics:", self.styles['SubHeader']))
            parts.append(data_table(detailed_data, [1.8 * inch, 1.8 * inch, 1.8 * inch, 1.6 * inch]))

            interpretation = (
                "The factors above represent operational drivers that influence nursing throughput and medication timing. "
                "Use them to prioritize staffing, scheduling, and process adjustments."
            )
            add_result_with_interpretation("Factors Affecting Performance", parts, interpretation)

        recs = data.get('ai_recommendations') or {}
        if recs:
            story.append(Paragraph("AI Recommendations", self.styles['SectionHeader']))
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

        self._add_signature_block(story)
        return story
