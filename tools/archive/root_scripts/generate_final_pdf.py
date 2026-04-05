import os
import json
from xhtml2pdf import pisa
from datetime import datetime

# Path Configuration
STORAGE_ROOT = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage"
SESSION_ID = "e56fbfa7-588d-4a77-81c4-856f1bedc3e6"
USER_ID = "e725ade1-1234-5678-90ab-cde456789012"
PROJECT_ID = "a7b8c9d0-1234-5678-90ab-cde456789012"

SESSION_DIR = os.path.join(STORAGE_ROOT, "users", USER_ID, PROJECT_ID, SESSION_ID)
INIT_FILE = os.path.join(SESSION_DIR, "session_init.json")
REPORT_FILE = os.path.join(SESSION_DIR, "forensic_report_v1.json")
OUTPUT_PDF = os.path.join(SESSION_DIR, "RICS_Forensic_Report.pdf")

def load_data():
    with open(INIT_FILE, 'r') as f:
        init_data = json.load(f)
    with open(REPORT_FILE, 'r') as f:
        report_data = json.load(f)
    return init_data, report_data

def generate_pdf():
    init_data, report_data = load_data()
    
    # Metadata
    address = init_data.get("address", {}).get("full_address", "64 Pinner Park Ave, Harrow HA2 6LF")
    date_str = datetime.now().strftime("%d %B %Y")
    
    # HTML Template (Premium Design)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{
                size: a4 portrait;
                @frame footer_frame {{
                    -pdf-frame-content: footer_content;
                    bottom: 1cm;
                    margin-left: 1cm;
                    margin-right: 1cm;
                    height: 1cm;
                }}
            }}
            body {{
                font-family: Helvetica, Arial, sans-serif;
                color: #333;
                line-height: 1.6;
            }}
            .header {{
                text-align: right;
                color: #c0392b;
                font-weight: bold;
                border-bottom: 2px solid #c0392b;
                padding-bottom: 5px;
            }}
            .title-page {{
                text-align: center;
                padding-top: 5cm;
                padding-bottom: 10cm;
            }}
            h1 {{
                font-size: 32pt;
                color: #2c3e50;
            }}
            .section {{
                margin-top: 30pt;
                page-break-before: always;
            }}
            h2 {{
                color: #c0392b;
                border-bottom: 1px solid #eee;
                padding-bottom: 10pt;
                font-size: 18pt;
            }}
            .room-block {{
                margin-bottom: 25pt;
                background-color: #fdfdfd;
                padding: 15pt;
                border: 1px solid #eee;
            }}
            .element-box {{
                margin-top: 10pt;
                padding: 10pt;
                background-color: #fff;
                border-left: 4pt solid #c0392b;
            }}
            .condition-tag {{
                display: inline-block;
                padding: 3pt 8pt;
                background-color: #c0392b;
                color: white;
                font-weight: bold;
                border-radius: 4pt;
                font-size: 10pt;
            }}
            .notes {{
                font-style: italic;
                color: #666;
                background: #f9f9f9;
                padding: 10pt;
                margin-top: 15pt;
            }}
            #footer_content {{
                text-align: center;
                color: #999;
                font-size: 9pt;
            }}
        </style>
    </head>
    <body>
        <div id="footer_content">
            RICS Home Survey Level 3 - Forensic Lab V2 - Page <pdf:pagenumber>
        </div>

        <div class="header">4SURE SMART INSPECTION</div>

        <div class="title-page">
            <h1>Building Survey Report</h1>
            <p style="font-size: 14pt;">RICS Level 3 Standard (Forensic V2)</p>
            <br><br>
            <p><strong>Property Address:</strong><br>{address}</p>
            <p><strong>Inspection Date:</strong> {date_str}</p>
            <p><strong>Surveyor:</strong> Expert Islam (RICS Accredited)</p>
        </div>

        <div class="section">
            <h2>Section D: Outside the Property</h2>
    """
    
    for room in report_data.get("rooms", []):
        html_content += f"""
        <div class="room-block">
            <h3>{room.get('room_id', 'External Area')}</h3>
        """
        for el in room.get("elements", []):
            html_content += f"""
            <div class="element-box">
                <p><strong>Component:</strong> {el.get('name')}</p>
                <div class="condition-tag">Condition: {el.get('condition_rating')}</div>
                <p><strong>Observation:</strong> {el.get('description')}</p>
                <p><strong>Defects identified:</strong> {", ".join(el.get('defects', []))}</p>
                <p><strong>Recommended Action:</strong> {el.get('actions')}</p>
            </div>
            """
        
        if room.get("notes"):
            html_content += f"""
            <div class="notes">
                <strong>Forensic Engineering Notes:</strong><br>
                {room.get('notes')}
            </div>
            """
        html_content += "</div>"

    html_content += """
        </div>
        
        <div class="section">
            <h2>Legal Disclosures & Risks</h2>
            <p>This report is generated using the RISC V2 Forensic Engine. The findings are intended for engineering validation and forensic training purposes.</p>
            <ul>
                <li><strong>Shared Drainage:</strong> Observations indicate certain components may serve multiple properties.</li>
                <li><strong>Structural Integrity:</strong> Fractures in cast iron components are considered critical failures.</li>
            </ul>
        </div>
    </body>
    </html>
    """

    # Run Conversion
    with open(OUTPUT_PDF, "wb") as f:
        pisa_status = pisa.CreatePDF(html_content, dest=f)
    
    return pisa_status.err

if __name__ == "__main__":
    err = generate_pdf()
    if not err:
        print(f"SUCCESS: PDF Generated at {OUTPUT_PDF}")
    else:
        print(f"ERROR: PDF Generation Failed with code {err}")
