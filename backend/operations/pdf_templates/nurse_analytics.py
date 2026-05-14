
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
        auth_text = f"System-generated report prepared by {name} on {ts} UTC. Controlled document. Do not distribute without authorization."
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

        def kv_table(items: list[list[str]]):
            t = Table(items, colWidths=[2.3 * inch, 4.7 * inch])
            t.setStyle(
                TableStyle(
                    [
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            return t

        def _num(v):
            try:
                n = float(v)
                if n != n:
                    return None
                return n
            except Exception:
                return None

        def _month_label():
            return datetime.now(timezone.utc).strftime("%B %Y")

        def add_three_part_section(section_title: str, analytics_result: str, why_text: str, recommendations: list[str]):
            story.append(Paragraph(section_title, self.styles["SectionHeader"]))
            story.append(Paragraph("Analytics Result", self.styles["SubHeader"]))
            story.append(Paragraph(analytics_result, self.styles["ContentText"]))
            story.append(Spacer(1, 0.06 * inch))
            story.append(Paragraph("Why (Contributing Factors)", self.styles["SubHeader"]))
            story.append(Paragraph(why_text, self.styles["ContentText"]))
            story.append(Spacer(1, 0.06 * inch))
            story.append(Paragraph("Solutions/Recommendations (Action Plan)", self.styles["SubHeader"]))
            if recommendations:
                for r in recommendations:
                    txt = str(r or "").strip()
                    if txt:
                        story.append(Paragraph(f"• {txt}", self.styles["ContentText"]))
            else:
                story.append(Paragraph("No action items are available for this section.", self.styles["ContentText"]))
            story.append(Spacer(1, 0.14 * inch))
        
        story.append(Paragraph("MediSync Monthly Health Intelligence Report", self.styles["ReportTitle"]))
        story.append(Spacer(1, 0.08 * inch))

        prepared_by = ""
        role_label = "Nurse"
        dept = ""
        if isinstance(self.user_info, dict):
            prepared_by = str(self.user_info.get("name") or "").strip()
            role_label = str(self.user_info.get("role") or role_label).strip() or role_label
            dept = str(self.user_info.get("department") or self.user_info.get("specialization") or "").strip()
        if not prepared_by:
            prepared_by = "MediSync System"
        month_lbl = _month_label()
        doc_id = f"MS-HIR-{datetime.now(timezone.utc).strftime('%Y-%m')}"
        doc_control = [
            ["Document Title", "MediSync Monthly Health Intelligence Report"],
            ["Document ID", doc_id],
            ["Report Period", month_lbl],
            ["Version", "1.0"],
            ["Prepared By", f"{prepared_by} ({role_label}{' - ' + dept if dept else ''})"],
            ["Reviewed By", "______________________________"],
            ["Approved By", "______________________________"],
            ["Distribution", "Controlled Copy"],
        ]
        story.append(Paragraph("Document Control (ISO 9001:2015)", self.styles["SectionHeader"]))
        story.append(kv_table(doc_control))
        story.append(Spacer(1, 0.12 * inch))
        
        results = data.get("analytics_results") or {}
        sources = data.get("interpretation_sources") or {}
        pf = data.get("performance_factors") or {}
        recs = data.get("ai_recommendations") or {}

        safe_recs = []
        if isinstance(recs, dict):
            for key in ("actionable", "resource", "strategies", "predictive"):
                items = recs.get(key) or []
                if not isinstance(items, list):
                    continue
                for it in items:
                    if isinstance(it, dict):
                        t = strip_confidence(str(it.get("text") or "").strip())
                    else:
                        t = strip_confidence(str(it).strip())
                    if t:
                        safe_recs.append(t)
        safe_recs = list(dict.fromkeys(safe_recs))[:10]

        story.append(Paragraph("Executive Overview", self.styles["SectionHeader"]))
        story.append(
            Paragraph(
                "This monthly report summarizes patient flow, common conditions, and medication needs in clear language. "
                "It is designed to support shift planning, supply readiness, and safe, timely patient care.",
                self.styles["ContentText"],
            )
        )
        story.append(Spacer(1, 0.14 * inch))

        story.append(Paragraph("Monthly Analytics Snapshot", self.styles["SectionHeader"]))
        if results and results.get("visualization"):
            try:
                img_buffer = self._to_image_buffer(results["visualization"])
                if img_buffer:
                    img = ReportLabImage(img_buffer)
                    img_width = 7 * inch
                    aspect = img.drawHeight / img.drawWidth if img.drawWidth else 1
                    img.drawWidth = img_width
                    img.drawHeight = img_width * aspect
                    story.append(img)
                    story.append(Spacer(1, 0.08 * inch))
            except Exception:
                pass

        add_three_part_section(
            "Monthly Analytics Snapshot (Plain-Language Summary)",
            "The snapshot summarizes this month’s workload, the most common conditions, and the main medications recommended by doctors.",
            "Changes typically reflect seasonal illness patterns, community behavior, and clinic capacity such as staffing and appointment availability.",
            [
                "Use this snapshot for shift planning and supply ordering for the next month.",
                "If the volume line is rising, prioritize morning shift coverage and triage flow.",
            ],
        )

        vp = sources.get("volume_prediction") if isinstance(sources, dict) else None
        fd = vp.get("forecasted_data") if isinstance(vp, dict) else []
        last = fd[-1] if isinstance(fd, list) and fd and isinstance(fd[-1], dict) else None
        last_pred = _num(last.get("predicted_volume")) if last else None
        volume_result = "Patient volume forecast is not available yet."
        if last and last_pred is not None:
            volume_result = f"Expected patient volume for {str(last.get('date') or 'the next period')}: about {int(round(last_pred))} patients."

        ht = sources.get("health_trends") if isinstance(sources, dict) else None
        top_list = ht.get("top_illnesses_by_week") if isinstance(ht, dict) else []
        top_row = next((x for x in top_list if isinstance(x, dict) and x.get("medical_condition")), None) if isinstance(top_list, list) else None
        top_condition = str(top_row.get("medical_condition")) if top_row else ""

        volume_why_bits = []
        if top_condition:
            volume_why_bits.append(f"Recent cases are led by {top_condition}, which can increase visits during peak weeks.")
        volume_why_bits.append("Volume also changes with season, weather, school schedules, public events, and staffing coverage.")
        volume_why = " ".join(volume_why_bits)

        volume_recs = [
            "Adjust shift coverage for the busiest time blocks and ensure triage support is staffed.",
            "Prepare a clear patient flow plan for peak days (queue monitoring, calling process, and escalation).",
            "If volume stays high for two months, recommend extra clinic sessions or extended hours on peak days.",
        ]
        if safe_recs:
            volume_recs.extend(safe_recs[:2])
        add_three_part_section("Patient Volume & Shift Planning", volume_result, volume_why, volume_recs)

        ma = sources.get("medication_analysis") if isinstance(sources, dict) else None
        pareto = ma.get("medication_pareto_data") if isinstance(ma, dict) else []
        top_meds = [str(r.get("medication")) for r in pareto[:3] if isinstance(r, dict) and r.get("medication")] if isinstance(pareto, list) else []
        med_result = "Medication recommendation data is not available yet."
        if top_meds:
            med_result = "Top doctor-recommended medications this month: " + ", ".join(top_meds) + "."
        med_why = (
            "Medication recommendations usually follow the most common conditions treated and local protocols. "
            "Shortages often occur when demand rises suddenly or when reorder points are not aligned with usage."
        )
        med_recs = []
        if top_meds:
            med_recs.append("Increase buffer stock for the top recommended medications for at least one extra week of demand.")
            med_recs.append("Review inventory reorder points and supplier lead times for these items.")
        med_recs.extend(
            [
                "Coordinate with pharmacy for daily availability checks during peak weeks.",
                "If a shortage risk is detected, prepare approved substitutes and update staff guidance.",
            ]
        )
        add_three_part_section("Medication Recommendations & Supply Readiness", med_result, med_why, med_recs)

        trends_result = "Condition trend data is not available yet."
        if top_row:
            count = _num(top_row.get("count")) or 0
            trends_result = f"The most common condition in the latest reporting window is {top_condition} ({int(count)} recorded cases)."
        trends_why = (
            "Condition patterns often follow seasonal cycles and community exposure. "
            "They can also change when reporting practices, referral patterns, or access to care changes."
        )
        trends_recs = [
            "Prepare triage prompts and patient guidance for the leading condition.",
            "Reinforce prevention and early care-seeking messaging through community health channels.",
            "Track week-to-week changes; persistent rises may require additional staffing and supplies.",
        ]
        add_three_part_section("Disease Trends (Top Conditions)", trends_result, trends_why, trends_recs)

        sig = pf.get("significant_factors") if isinstance(pf, dict) else []
        drivers = []
        if isinstance(sig, list):
            for s in sig:
                txt = str(s or "").strip()
                if not txt:
                    continue
                drivers.append(txt.split(":")[0].strip() if ":" in txt else txt)
        drivers = list(dict.fromkeys([d for d in drivers if d]))[:5]
        ops_result = "Operational drivers are not available yet."
        if drivers:
            ops_result = "The system flagged the following drivers as most linked to service delays and workload changes: " + ", ".join(drivers) + "."
        ops_why = (
            "These drivers can create patient backlogs when they worsen (for example, uneven staffing across shifts or longer waiting times). "
            "Small process delays can compound during peak hours."
        )
        ops_recs = [
            "Standardize the start-of-shift checklist (queue status, staffing coverage, and supply readiness).",
            "Use a short daily huddle before peak hours to redistribute staff if needed.",
            "Record recurring bottlenecks and implement one improvement per month (continuous improvement).",
        ]
        add_three_part_section("Service Quality & Continuous Improvement", ops_result, ops_why, ops_recs)

        add_three_part_section(
            "Overall Action Plan (LGU-Ready)",
            "The monthly priority is to match staff coverage and supplies to expected demand and leading conditions.",
            "If patient volume and top conditions rise together, crowding risk increases unless capacity is adjusted early.",
            [
                "High Priority: reinforce morning shift coverage and triage support; ensure clear queue flow and escalation.",
                "Medium Priority: increase buffer stock for top recommended medicines and monitor inventory weekly.",
                "Low Priority: update community education aligned with the leading condition and observed demand patterns.",
            ],
        )
        return story
