
import io
import os
from abc import ABC, abstractmethod
from reportlab.lib import colors
from reportlab.lib.colors import CMYKColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from PIL import Image

class BasePDFTemplate(ABC):
    def __init__(self, buffer, hospital_info, user_info=None, logo_path=None, page_size=A4):
        self.buffer = buffer
        self.hospital_info = hospital_info
        self.user_info = user_info
        self.logo_path = logo_path
        self.page_size = page_size
        self.width, self.height = page_size
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.primary_color = colors.black
        self.accent_color = colors.black
        base_font = "Helvetica"
        base_font_bold = "Helvetica-Bold"
        base_size = 11
        base_leading = 14
        
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontName=base_font_bold,
            fontSize=base_size,
            leading=base_leading,
            spaceAfter=12,
            textColor=self.primary_color,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontName=base_font_bold,
            fontSize=base_size,
            leading=base_leading,
            spaceAfter=8,
            textColor=self.primary_color,
            borderPadding=5,
            borderColor=self.accent_color,
            borderWidth=0,
            borderBottomWidth=1
        ))
        
        self.styles.add(ParagraphStyle(
            name='ContentText',
            parent=self.styles['Normal'],
            fontName=base_font,
            fontSize=base_size,
            leading=base_leading,
            textColor=self.primary_color,
            alignment=TA_JUSTIFY
        ))
        
        self.styles.add(ParagraphStyle(
            name='FooterText',
            parent=self.styles['Normal'],
            fontName=base_font,
            fontSize=base_size,
            leading=base_leading,
            textColor=self.primary_color,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontName=base_font_bold,
            fontSize=base_size,
            leading=base_leading,
            spaceAfter=6,
            textColor=self.primary_color,
            alignment=TA_LEFT
        ))

        self.styles.add(ParagraphStyle(
            name='SignatureLabelRight',
            parent=self.styles['Normal'],
            fontName=base_font_bold,
            fontSize=base_size,
            leading=base_leading,
            textColor=self.primary_color,
            alignment=TA_RIGHT
        ))

        self.styles.add(ParagraphStyle(
            name='SignatureValueLeft',
            parent=self.styles['Normal'],
            fontName=base_font,
            fontSize=base_size,
            leading=base_leading,
            textColor=self.primary_color,
            alignment=TA_LEFT
        ))

    def _to_bw_image_reader(self, source):
        try:
            if isinstance(source, (str, bytes, os.PathLike)):
                img = Image.open(source)
            else:
                source.seek(0)
                img = Image.open(source)
            img = img.convert("RGB")
            img_l = img.convert("L")
            img_bw = img_l.point(lambda p: 255 if p > 200 else 0).convert("1")
            return ImageReader(img_bw)
        except Exception:
            return None

    def _to_bw_image_buffer(self, source):
        try:
            if isinstance(source, (str, bytes, os.PathLike)):
                img = Image.open(source)
            else:
                source.seek(0)
                img = Image.open(source)
            img = img.convert("RGB")
            img_l = img.convert("L")
            img_bw = img_l.point(lambda p: 255 if p > 200 else 0).convert("1")
            buffer = io.BytesIO()
            img_bw.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
        except Exception:
            return None

    def _to_image_buffer(self, source):
        try:
            if source is None:
                return None
            if isinstance(source, (str, os.PathLike)):
                img = Image.open(source)
            elif isinstance(source, (bytes, bytearray)):
                img = Image.open(io.BytesIO(source))
            else:
                source.seek(0)
                img = Image.open(source)
            img = img.convert("RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
        except Exception:
            return None

    def _draw_wrapped_canvas_text(self, canvas_obj, text, x, y, max_width, line_height):
        if not text:
            return y
        words = str(text).split()
        if not words:
            return y
        line = ""
        for w in words:
            candidate = f"{line} {w}".strip()
            if canvas_obj.stringWidth(candidate, canvas_obj._fontname, canvas_obj._fontsize) <= max_width:
                line = candidate
            else:
                canvas_obj.drawString(x, y, line)
                y -= line_height
                line = w
        if line:
            canvas_obj.drawString(x, y, line)
            y -= line_height
        return y

    def _draw_header(self, canvas, doc):
        """
        Draws the header with logo (left), hospital info (right), and a full-width divider line.
        """
        canvas.saveState()
        
        margin = 0.5 * inch
        logo_max_height = 1.2 * inch
        logo_y = self.height - margin - logo_max_height
        
        text_x = margin
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img_reader = self._to_bw_image_reader(self.logo_path)
                if img_reader:
                    pil_img = Image.open(self.logo_path)
                    w, h = pil_img.size
                    aspect = (w / h) if h else 1
                    draw_h = logo_max_height
                    draw_w = draw_h * aspect
                    canvas.drawImage(img_reader, margin, logo_y, width=draw_w, height=draw_h, mask=None, preserveAspectRatio=True)
                    text_x = margin + draw_w + 0.3 * inch
            except Exception as e:
                print(f"Error drawing logo: {e}")
                text_x = margin

        # Hospital Info
        canvas.setFillColor(self.primary_color)
        
        canvas.setFont("Helvetica-Bold", 11)
        cursor_y = logo_y + logo_max_height - 2
        max_text_width = (self.width - margin) - text_x
        cursor_y = self._draw_wrapped_canvas_text(canvas, self.hospital_info.get('name', 'Hospital Name'), text_x, cursor_y, max_text_width, 14)
        canvas.setFont("Helvetica", 11)
        cursor_y = self._draw_wrapped_canvas_text(canvas, self.hospital_info.get('address', 'Hospital Address'), text_x, cursor_y, max_text_width, 14)
        dept = ""
        if isinstance(self.user_info, dict):
            dept = str(self.user_info.get("department") or self.user_info.get("specialization") or "").strip()
        if not dept:
            dept = str(self.hospital_info.get("department") or "").strip()
        if dept:
            cursor_y = self._draw_wrapped_canvas_text(canvas, f"Department: {dept}", text_x, cursor_y, max_text_width, 14)
        
        # Draw Divider Line
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1)
        line_y = min(logo_y, cursor_y + 12) - 4
        canvas.line(margin, line_y, self.width - margin, line_y)
        
        canvas.restoreState()

    def _draw_footer(self, canvas, doc):
        """
        Draws the footer with page number and generation info.
        """
        canvas.saveState()
        margin = 0.5 * inch
        
        canvas.setFont("Helvetica", 11)
        canvas.setFillColor(colors.black)
        
        # Page Number
        page_num = f"Page {doc.page}"
        canvas.drawRightString(self.width - margin, margin, page_num)
        
        canvas.restoreState()

    def _add_signature_block(self, story):
        if not isinstance(self.user_info, dict):
            return
        name = str(self.user_info.get("name") or "").strip()
        specialization = str(self.user_info.get("specialization") or self.user_info.get("department") or "").strip()
        if not name:
            return

        story.append(Spacer(1, 0.35 * inch))

        available_width = self.width - (2 * 0.5 * inch)
        left_w = available_width * 0.6
        right_w = available_width * 0.4

        block = [
            Paragraph("Prepared by:", self.styles["SignatureLabelRight"]),
            Paragraph(f"{name} (sgd)", self.styles["SignatureValueLeft"]),
        ]
        if specialization:
            block.append(Paragraph(str(specialization), self.styles["SignatureValueLeft"]))
        else:
            block.append(Paragraph(" ", self.styles["SignatureValueLeft"]))

        signature_table = Table([[Paragraph("", self.styles["ContentText"]), block]], colWidths=[left_w, right_w])
        signature_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(signature_table)

    def generate(self, data):
        """
        Main generation method.
        """
        margin = 0.5 * inch
        top_margin = 2.0 * inch
        bottom_margin = getattr(self, "bottom_margin", 0.75 * inch)
        
        frame = Frame(
            margin, 
            bottom_margin, 
            self.width - 2*margin, 
            self.height - top_margin - bottom_margin,
            id='normal',
            showBoundary=0
        )
        
        template = PageTemplate(id='main', frames=frame, onPage=self._on_page)
        doc = BaseDocTemplate(
            self.buffer,
            pagesize=self.page_size,
            rightMargin=margin,
            leftMargin=margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
            title="MediSync Report",
            author="MediSync System"
        )
        doc.addPageTemplates([template])
        
        story = self.build_story(data)
        doc.build(story)

    def _on_page(self, canvas, doc):
        self._draw_header(canvas, doc)
        self._draw_footer(canvas, doc)

    @abstractmethod
    def build_story(self, data):
        """
        To be implemented by subclasses to define content structure.
        """
        pass
