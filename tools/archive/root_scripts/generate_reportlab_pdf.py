import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

# Path Configuration
STORAGE_ROOT = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage"
SESSION_ID = "7fb61b31-60d0-41b0-aec3-cc5b561d86b5"
USER_ID = "e725ade1-1234-5678-90ab-cde456789012"
PROJECT_ID = "a7b8c9d0-1234-5678-90ab-cde456789012"

SESSION_DIR = os.path.join(STORAGE_ROOT, "users", USER_ID, PROJECT_ID, SESSION_ID)
INIT_FILE = os.path.join(SESSION_DIR, "session_init.json")
REPORT_FILE = os.path.join(SESSION_DIR, "forensic_report_v1.json")
OUTPUT_PDF = os.path.join(SESSION_DIR, "RICS_Forensic_Report_Scenario_2.pdf")

def load_data():
    if not os.path.exists(INIT_FILE) or not os.path.exists(REPORT_FILE):
        return None, None
    with open(INIT_FILE, 'r') as f:
        init_data = json.load(f)
    with open(REPORT_FILE, 'r') as f:
        report_data = json.load(f)
    return init_data, report_data

def generate_pdf():
    init_data, report_data = load_data()
    if not init_data:
        return "Missing data files."
    
    doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    styles.add(ParagraphStyle(name='TitlePageTitle', fontName='Helvetica-Bold', fontSize=28, alignment=1, spaceAfter=20, textColor=colors.HexColor("#2C3E50")))
    styles.add(ParagraphStyle(name='SectionHeader', fontName='Helvetica-Bold', fontSize=18, spaceBefore=20, spaceAfter=10, textColor=colors.HexColor("#C0392B"), borderPadding=5, borderSide="bottom", borderWidth=1))
    styles.add(ParagraphStyle(name='RoomHeader', fontName='Helvetica-Bold', fontSize=14, spaceBefore=15, spaceAfter=5, textColor=colors.HexColor("#2980B9")))
    styles.add(ParagraphStyle(name='ElementTitle', fontName='Helvetica-Bold', fontSize=12, spaceBefore=5))
    styles.add(ParagraphStyle(name='ConditionRating', fontName='Helvetica-Bold', fontSize=10, textColor=colors.white, backColor=colors.HexColor("#C0392B"), borderPadding=3, borderRadius=4))
    styles.add(ParagraphStyle(name='AnalysisBox', fontName='Helvetica-Oblique', fontSize=10, leftIndent=10, rightIndent=10, spaceBefore=10, spaceAfter=10, backColor=colors.HexColor("#F5F5F5"), borderPadding=10))

    elements = []

    # Title Page
    elements.append(Spacer(1, 150))
    elements.append(Paragraph("Building Survey Report", styles['TitlePageTitle']))
    elements.append(Paragraph("RICS Level 3 Standard - Forensic Lab V2", styles['Normal']))
    elements.append(Spacer(1, 50))
    
    address = init_data.get("address", {}).get("full_address", "64 Pinner Park Ave, Harrow HA2 6LF")
    date_str = datetime.now().strftime("%d %B %Y")
    
    data = [
        ["Property Address:", address],
        ["Date of Inspection:", date_str],
        ["Surveyor:", "Expert Islam (RICS Accredited)"],
        ["Session ID:", SESSION_ID]
    ]
    t = Table(data, colWidths=[120, 300])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('PADDING', (0,0), (-1,-1), 10)
    ]))
    elements.append(t)
    elements.append(PageBreak())

    # Section D: Outside
    elements.append(Paragraph("Section D: Outside the Property", styles['SectionHeader']))
    
    for room in report_data.get("rooms", []):
        elements.append(Paragraph(f"Room/Area: {room.get('room_id')}", styles['RoomHeader']))
        
        for el in room.get("elements", []):
            elements.append(Paragraph(f"Component: {el.get('name')}", styles['ElementTitle']))
            elements.append(Paragraph(f"Condition: {el.get('condition_rating')}", styles['ConditionRating']))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph(f"<b>Description:</b> {el.get('description')}", styles['Normal']))
            elements.append(Paragraph(f"<b>Defects:</b> {', '.join(el.get('defects', []))}", styles['Normal']))
            elements.append(Paragraph(f"<b>Actions:</b> {el.get('actions')}", styles['Normal']))
            elements.append(Spacer(1, 10))
            
        if room.get("notes"):
            elements.append(Paragraph("<b>Forensic Engineering Observations:</b>", styles['Normal']))
            elements.append(Paragraph(room.get('notes'), styles['AnalysisBox']))
            
    # Section I: Risks
    elements.append(PageBreak())
    elements.append(Paragraph("Section I: Risks & Required Actions", styles['SectionHeader']))
    elements.append(Paragraph("The following items require immediate engineering attention as identified by the Forensic Engine:", styles['Normal']))
    
    risk_data = [
        ["Risk Type", "Impact", "Recommendation"],
        ["Structural Failure", "Life Safety / Collapse", "Immediate replacement of cast iron components"],
        ["Drainage Integrity", "Flooding / Debris", "High pressure flush and CCTV validation"],
        ["Public Liability", "Trip Hazard", "Cordon off area until rectification"]
    ]
    rt = Table(risk_data, colWidths=[100, 150, 200])
    rt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#C0392B")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    elements.append(rt)

    # Build PDF
    doc.build(elements)
    return None

if __name__ == "__main__":
    err = generate_pdf()
    if not err:
        print(f"SUCCESS: PDF Generated at {OUTPUT_PDF}")
    else:
        print(f"ERROR: {err}")
