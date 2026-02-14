
import os
from abc import ABC, abstractmethod
from reportlab.lib import colors
from reportlab.lib.colors import CMYKColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

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
        # Consistent text color scheme (CMYK Black for professional print)
        self.primary_color = CMYKColor(0, 0, 0, 1)  # Black
        self.accent_color = CMYKColor(1, 0.6, 0, 0) # Blue-ish (C=100, M=60)
        
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            leading=22,
            spaceAfter=20,
            textColor=self.primary_color,
            alignment=1 # Center
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            leading=16,
            spaceAfter=12,
            textColor=self.primary_color,
            borderPadding=5,
            borderColor=self.accent_color,
            borderWidth=0,
            borderBottomWidth=1
        ))
        
        self.styles.add(ParagraphStyle(
            name='ContentText',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=self.primary_color
        ))
        
        self.styles.add(ParagraphStyle(
            name='FooterText',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.grey
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            leading=14,
            spaceAfter=8,
            textColor=self.primary_color,
            fontName='Helvetica-Bold'
        ))

    def _draw_header(self, canvas, doc):
        """
        Draws the header with transparent logo and hospital info.
        """
        canvas.saveState()
        
        # Logo - Transparent background, original dimensions (scaled to fit constraint)
        # Constraint: Top-left, max height 1.2 inch
        margin = 0.5 * inch
        logo_max_height = 1.2 * inch
        logo_y = self.height - margin - logo_max_height
        
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                # Use mask='auto' for transparency if using simple drawImage
                # Or ReportLab handles PNG alpha channel automatically
                img = ReportLabImage(self.logo_path)
                img_w = img.drawWidth
                img_h = img.drawHeight
                
                # Scale maintaining aspect ratio
                aspect = img_w / img_h
                draw_h = logo_max_height
                draw_w = draw_h * aspect
                
                canvas.drawImage(self.logo_path, margin, logo_y, width=draw_w, height=draw_h, mask='auto', preserveAspectRatio=True)
                
                # Text offset
                text_x = margin + draw_w + 0.3 * inch
            except Exception as e:
                print(f"Error drawing logo: {e}")
                text_x = margin
        else:
            text_x = margin

        # Hospital Info
        canvas.setFillColor(self.primary_color)
        
        canvas.setFont("Helvetica-Bold", 14)
        name_y = logo_y + logo_max_height - 0.3*inch
        canvas.drawString(text_x, name_y, self.hospital_info.get('name', 'Hospital Name'))
        
        canvas.setFont("Helvetica", 11)
        addr_y = name_y - 15
        canvas.drawString(text_x, addr_y, self.hospital_info.get('address', 'Hospital Address'))
        
        # Draw Divider Line
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(0.5)
        line_y = logo_y - 10
        canvas.line(margin, line_y, self.width - margin, line_y)
        
        canvas.restoreState()

    def _draw_footer(self, canvas, doc):
        """
        Draws the footer with page number and generation info.
        """
        canvas.saveState()
        margin = 0.5 * inch
        
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        
        # Page Number
        page_num = f"Page {doc.page}"
        canvas.drawRightString(self.width - margin, margin, page_num)
        
        # Generation Info
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        footer_text = f"Generated by MediSync on {timestamp} | {self.hospital_info.get('name', 'MediSync')}"
        canvas.drawString(margin, margin, footer_text)
        
        canvas.restoreState()

    def generate(self, data):
        """
        Main generation method.
        """
        margin = 0.5 * inch
        top_margin = 2.0 * inch # Space for header
        bottom_margin = 0.75 * inch # Space for footer
        
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
