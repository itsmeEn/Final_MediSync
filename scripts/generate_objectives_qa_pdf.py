from pathlib import Path
import re

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak


ROOT = Path(__file__).resolve().parents[1]
INPUT_MD = ROOT / "docs" / "OVERALL_SYSTEM_OBJECTIVES_QA.md"
OUTPUT_PDF = ROOT / "docs" / "OVERALL_SYSTEM_OBJECTIVES_QA.pdf"


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _parse_markdown(lines: list[str]):
    blocks: list[tuple[str, object]] = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")

        if not line.strip():
            i += 1
            continue

        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            blocks.append(("heading", (level, m.group(2).strip())))
            i += 1
            continue

        if line.startswith("Q: "):
            q = line[3:].strip()
            a_lines: list[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i].rstrip("\n")
                if nxt.startswith("A: "):
                    a_lines.append(nxt[3:].strip())
                    i += 1
                    break
                if nxt.strip():
                    break
                i += 1

            bullets: list[str] = []
            while i < len(lines):
                nxt = lines[i].rstrip("\n")
                if nxt.startswith("- "):
                    bullets.append(nxt[2:].strip())
                    i += 1
                    continue
                if not nxt.strip():
                    i += 1
                    continue
                break

            a = " ".join([x for x in a_lines if x])
            blocks.append(("qa", (q, a, bullets)))
            continue

        if line.startswith("- "):
            bullets: list[str] = []
            while i < len(lines) and lines[i].rstrip("\n").startswith("- "):
                bullets.append(lines[i].rstrip("\n")[2:].strip())
                i += 1
            blocks.append(("bullets", bullets))
            continue

        para_lines = [line.strip()]
        i += 1
        while i < len(lines):
            nxt = lines[i].rstrip("\n")
            if not nxt.strip():
                i += 1
                break
            if re.match(r"^(#{1,3})\s+", nxt) or nxt.startswith("Q: ") or nxt.startswith("- "):
                break
            para_lines.append(nxt.strip())
            i += 1
        blocks.append(("p", " ".join(para_lines).strip()))

    return blocks


def main():
    if not INPUT_MD.exists():
        raise SystemExit(f"Missing input markdown: {INPUT_MD}")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], spaceAfter=18)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceBefore=12, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], spaceAfter=8, leading=14)
    q_style = ParagraphStyle("q", parent=styles["BodyText"], spaceBefore=6, spaceAfter=4, leading=14)
    a_style = ParagraphStyle("a", parent=styles["BodyText"], spaceAfter=8, leftIndent=12, leading=14)

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
        title="MediSync Overall System Q&A (Objective-Focused)",
    )

    lines = INPUT_MD.read_text(encoding="utf-8").splitlines(True)
    blocks = _parse_markdown(lines)

    story = []
    first_title_done = False

    for kind, payload in blocks:
        if kind == "heading":
            level, text = payload
            text = _escape(str(text))
            if level == 1:
                if not first_title_done:
                    story.append(Paragraph(text, title_style))
                    first_title_done = True
                else:
                    story.append(PageBreak())
                    story.append(Paragraph(text, h1))
            elif level == 2:
                story.append(Paragraph(text, h2))
            else:
                story.append(Paragraph(text, h3))
            continue

        if kind == "p":
            story.append(Paragraph(_escape(str(payload)), body))
            continue

        if kind == "bullets":
            items = [
                ListItem(Paragraph(_escape(b), body), leftIndent=18)
                for b in payload
            ]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
            story.append(Spacer(1, 6))
            continue

        if kind == "qa":
            q, a, bullets = payload
            story.append(Paragraph(f"<b>Q:</b> {_escape(q)}", q_style))
            story.append(Paragraph(f"<b>A:</b> {_escape(a)}", a_style))
            if bullets:
                items = [
                    ListItem(Paragraph(_escape(b), body), leftIndent=24)
                    for b in bullets
                ]
                story.append(ListFlowable(items, bulletType="bullet", leftIndent=24))
                story.append(Spacer(1, 6))
            continue

    doc.build(story)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

