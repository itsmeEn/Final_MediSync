
import io
import os
from reportlab.lib import colors
from reportlab.lib.colors import CMYKColor
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.utils import ImageReader

class ProfessionalPDFGenerator:
    def __init__(self, buffer, hospital_info, logo_path=None, page_size=A4):
        self.buffer = buffer
        self.hospital_info = hospital_info
        self.logo_path = logo_path
        self.page_size = page_size
        self.width, self.height = page_size
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        # Define custom styles
        cmyk_black = CMYKColor(0, 0, 0, 1)
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            leading=16,
            spaceAfter=12,
            textColor=cmyk_black
        ))
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12,
        ))

    def _draw_header(self, canvas, doc):
        """
        Draws the professional header on every page.
        """
        canvas.saveState()
        
        # 1. Logo Placement (Upper left, 1.5" diameter)
        # Position: Top left margin. Let's say (0.5 inch, Height - 0.5 inch - 1.5 inch)
        margin = 0.5 * inch
        logo_size = 1.5 * inch
        logo_x = margin
        logo_y = self.height - margin - logo_size
        
        # Draw Circle Border/Clip
        # Center of circle
        cx = logo_x + logo_size / 2
        cy = logo_y + logo_size / 2
        radius = logo_size / 2

        # Draw logo if exists
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                # Create a circular clipping path
                path = canvas.beginPath()
                path.circle(cx, cy, radius)
                canvas.clipPath(path, stroke=0, fill=0)
                
                # Draw image
                canvas.drawImage(self.logo_path, logo_x, logo_y, width=logo_size, height=logo_size, preserveAspectRatio=True, anchor='c')
                
                # Reset clip
                canvas.restoreState()
                canvas.saveState() # Save again for text
            except Exception as e:
                print(f"Error drawing logo: {e}")
                # Fallback: Draw circle outline
                canvas.circle(cx, cy, radius, stroke=1, fill=0)
        else:
            # Placeholder circle
            canvas.circle(cx, cy, radius, stroke=1, fill=0)
            canvas.setFont("Helvetica", 8)
            canvas.drawCentredString(cx, cy, "LOGO")

        # 2. Text Elements
        # Position: Right of logo (0.25 inch gap)
        text_x = logo_x + logo_size + 0.25 * inch
        # Vertically center aligned with logo? 
        # "Positioned immediately right of the logo (aligned vertically center)" -> This might mean the block is centered relative to the logo height.
        
        # Let's calculate Y positions.
        # Hospital Name: Size 13pt, Bold.
        # Address: Size 12pt, Regular.
        # Department: Size 12pt, Regular.
        
        # Total height of text block approx: 15 + 14 + 14 = 43 pts (~0.6 inch).
        # Logo height is 1.5 inch.
        # Center Y of logo is `cy`.
        # Start Y of text block should be cy + (text_height / 2).
        
        cmyk_black = CMYKColor(0, 0, 0, 1)
        canvas.setFillColor(cmyk_black) # Pure black CMYK
        
        # Hospital Name
        canvas.setFont("Helvetica-Bold", 13)
        name_y = cy + 10 # Adjust for baseline
        canvas.drawString(text_x, name_y, self.hospital_info.get('name', 'Hospital Name'))
        
        # Address
        canvas.setFont("Helvetica", 12)
        addr_y = name_y - 15
        canvas.drawString(text_x, addr_y, self.hospital_info.get('address', '123 Hospital Address'))
        
        # Department
        dept_y = addr_y - 15
        canvas.drawString(text_x, dept_y, self.hospital_info.get('department', 'Department Name'))
        
        canvas.restoreState()

        # Draw a line separator? (Optional, not requested but good for "Professional")
        # canvas.line(margin, logo_y - 0.2*inch, self.width - margin, logo_y - 0.2*inch)

    def generate(self, patient_records, analytics_charts=None):
        """
        Generates the PDF document.
        :param patient_records: List of dictionaries or list of lists for the table.
        :param analytics_charts: List of image buffers (BytesIO) or paths for charts.
        """
        # Margins: 0.5 inch all around.
        # Header takes up space. Top margin needs to accommodate header.
        # Header starts at top-0.5inch, height 1.5inch. 
        # So content should start below that.
        # Top Margin = 0.5 + 1.5 + 0.25 (gap) = 2.25 inch.
        
        margin = 0.5 * inch
        top_margin = 2.5 * inch # Adequate space for header
        
        frame = Frame(
            margin, 
            margin, 
            self.width - 2*margin, 
            self.height - top_margin - margin,
            id='normal',
            showBoundary=0
        )
        
        template = PageTemplate(id='test', frames=frame, onPage=self._draw_header)
        doc = BaseDocTemplate(
            self.buffer,
            pagesize=self.page_size,
            rightMargin=margin,
            leftMargin=margin,
            topMargin=top_margin,
            bottomMargin=margin
        )
        doc.addPageTemplates([template])
        
        story = []
        
        # 1. Patient Records Section
        story.append(Paragraph("Patient Records", self.styles['SectionHeader']))
        
        if patient_records:
            # Prepare table data
            # headers = patient_records[0].keys() if isinstance(patient_records[0], dict) else []
            # For simplicity, assume passed as list of lists including header
            
            # Style for table
            t_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ])
            
            t = Table(patient_records, repeatRows=1)
            # Auto-width calculation is tricky, ReportLab tries its best or use colWidths
            # Assuming A4 width ~8inch, margins 1inch total -> 7inch usable.
            available_width = self.width - 2*margin
            col_count = len(patient_records[0])
            if col_count > 0:
                col_w = available_width / col_count
                t._argW = [col_w] * col_count
            
            t.setStyle(t_style)
            story.append(t)
        else:
            story.append(Paragraph("No records found.", self.styles['NormalText']))
            
        story.append(Spacer(1, 0.5 * inch))
        
        # 2. Analytics Results Section
        story.append(Paragraph("Analytics Results", self.styles['SectionHeader']))
        
        if analytics_charts:
            for chart_buffer in analytics_charts:
                # Add chart image
                # Ensure high resolution (dpi) is handled by the image source, ReportLab scales it.
                # Assuming chart_buffer is a BytesIO or path
                img = ReportLabImage(chart_buffer)
                
                # Scale image to fit page width
                avail_width = self.width - 2*margin
                img_width = img.drawWidth
                img_height = img.drawHeight
                
                factor = avail_width / img_width
                img.drawWidth = avail_width
                img.drawHeight = img_height * factor
                
                story.append(img)
                story.append(Spacer(1, 0.25 * inch))
                
                # Label?
                story.append(Paragraph("Figure: Analytics Data Visualization", self.styles['Italic']))
                story.append(Spacer(1, 0.5 * inch))

        doc.build(story)

