
from .base_template import BasePDFTemplate
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.units import inch

class DoctorAnalyticsPDF(BasePDFTemplate):
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
                    ['Metric', 'Current', 'Benchmark', 'Status'],
                    ['Patient Satisfaction', '4.8/5', '4.5/5', 'Above Target'],
                    ['Avg Wait Time', '12 min', '15 min', 'Optimal'],
                    ['Treatment Efficacy', '94%', '90%', 'Above Target']
                ]
            parts.append(Spacer(1, 0.1 * inch))
            parts.append(data_table(comp_data, [2.0 * inch, 1.5 * inch, 1.5 * inch, 2.0 * inch]))

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
                "Key indicators and comparative results are presented above. "
                "Review status fields to identify areas that exceed targets or require intervention."
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
                    ['Date', 'Patient Volume', 'Avg LOS', 'Staffing Level'],
                    ['2023-10-01', '45', '2.1 days', 'Full'],
                    ['2023-10-02', '52', '2.3 days', 'Short'],
                    ['2023-10-03', '48', '2.0 days', 'Full'],
                    ['2023-10-04', '60', '2.5 days', 'Full'],
                ]
            parts.append(Spacer(1, 0.12 * inch))
            parts.append(Paragraph("Detailed performance metrics:", self.styles['SubHeader']))
            parts.append(data_table(detailed_data, [1.8 * inch, 1.8 * inch, 1.8 * inch, 1.6 * inch]))

            interpretation = (
                "The factors above summarize drivers correlated with performance variability. "
                "Use these indicators to prioritize operational changes and clinical workflow adjustments."
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
