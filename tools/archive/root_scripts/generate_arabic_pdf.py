import os
import json
from datetime import datetime
import google.generativeai as genai
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Path Configuration
STORAGE_ROOT = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage"
SESSION_ID = "7fb61b31-60d0-41b0-aec3-cc5b561d86b5"
USER_ID = "e725ade1-1234-5678-90ab-cde456789012"
PROJECT_ID = "a7b8c9d0-1234-5678-90ab-cde456789012"

SESSION_DIR = os.path.join(STORAGE_ROOT, "users", USER_ID, PROJECT_ID, SESSION_ID)
INIT_FILE = os.path.join(SESSION_DIR, "session_init.json")
REPORT_FILE = os.path.join(SESSION_DIR, "forensic_report_v1.json")
OUTPUT_PDF = os.path.join(SESSION_DIR, "RICS_Forensic_Report_Arabic.pdf")

# Register Arabic Font
pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))

# Configure AI
genai.configure(api_key="AIzaSyC0CQ-L_yuBaVDftsNV56FQZUwUr_3ohKo")
model = genai.GenerativeModel('models/gemini-2.5-flash')

def translate_report(data):
    # Simplified translation for speed
    prompt = f"Translate the following RICS inspection findings to professional Arabic engineering language. Keep IDs and technical codes (like BS EN 124) as is. Return as JSON with same structure: {json.dumps(data)}"
    response = model.generate_content(prompt)
    try:
        # Clean JSON markdown
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except:
        return data # Fallback to English if translation fails

def fix_arabic(text):
    if not text: return ""
    reshaped_text = reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def generate_arabic_pdf():
    with open(INIT_FILE, 'r') as f:
        init_data = json.load(f)
    with open(REPORT_FILE, 'r') as f:
        en_report = json.load(f)
    
    ar_report = translate_report(en_report)
    
    doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom Arabic Styles
    ar_style = ParagraphStyle(
        name='ArabicNormal',
        fontName='Arial',
        fontSize=12,
        alignment=2, # Right
        leading=16
    )
    ar_title = ParagraphStyle(
        name='ArabicTitle',
        fontName='Arial',
        fontSize=24,
        alignment=1,
        spaceAfter=30,
        textColor=colors.HexColor("#2C3E50")
    )
    ar_section = ParagraphStyle(
        name='ArabicSection',
        fontName='Arial',
        fontSize=18,
        alignment=2,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#C0392B")
    )

    elements = []
    
    # Title Page
    elements.append(Spacer(1, 200))
    elements.append(Paragraph(fix_arabic("تقرير مسح المباني - تقييم فني"), ar_title))
    elements.append(Paragraph(fix_arabic("المعيار: RICS المستوى الثالث"), ar_style))
    elements.append(Spacer(1, 50))
    
    address = fix_arabic(init_data.get("address", {}).get("full_address", "Harrow, London"))
    date_str = fix_arabic(datetime.now().strftime("%d %B %Y"))
    
    data = [
        [address, fix_arabic(":عنوان العقار")],
        [date_str, fix_arabic(":تاريخ المعاينة")],
        [fix_arabic("إسلام جلال (خبير معتمد)"), fix_arabic(":اسم المساح")]
    ]
    t = Table(data, colWidths=[300, 100])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Arial'),
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    elements.append(t)
    elements.append(PageBreak())

    # Content
    elements.append(Paragraph(fix_arabic("القسم D: خارج العقار"), ar_section))
    
    for room in ar_report.get("rooms", []):
        elements.append(Paragraph(fix_arabic(f"المنطقة: {room.get('room_id')}"), ar_style))
        for el in room.get("elements", []):
            elements.append(Paragraph(fix_arabic(f"المكون: {el.get('name')}"), ar_style))
            elements.append(Paragraph(fix_arabic(f"التقييم: {el.get('condition_rating')}"), ar_style))
            elements.append(Paragraph(fix_arabic(f"الوصف: {el.get('description')}"), ar_style))
            elements.append(Paragraph(fix_arabic(f"التوصية: {el.get('actions')}"), ar_style))
            elements.append(Spacer(1, 10))
            
    doc.build(elements)
    return None

if __name__ == "__main__":
    generate_arabic_pdf()
    print(f"SUCCESS: Arabic PDF Generated at {OUTPUT_PDF}")
