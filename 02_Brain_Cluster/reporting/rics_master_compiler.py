import os
import json
from datetime import datetime
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

class RICSMasterCompiler:
    def __init__(self):
        # Setup Jinja2 Environment for the Master Template
        template_dir = os.path.join(os.path.dirname(__file__), "templates", "rics_v3")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template("master.html")
        
        self.output_dir = os.path.join(os.path.dirname(__file__), "generated", "rics")
        os.makedirs(self.output_dir, exist_ok=True)

    async def compile_final_pdf(self, project_id: str) -> str:
        """
        1. Loads the Executive Summary (Phase 3).
        2. Scans for all APPROVED `_final.json` room files (Phase 4).
        3. Renders the Master HTML Template.
        4. Converts to locked PDF.
        """
        print(f"[{project_id}] Starting Master PDF Compilation...")
        
        from services.synthesis_engine import _resolve_project_semantic_path
        project_dir = await _resolve_project_semantic_path(project_id)
        if not project_dir:
            raise ValueError(f"Project directory not found for {project_id}")
            
        # 1. Load Executive Summary (Property_Master_State.json)
        master_state_path = os.path.join(project_dir, "Property_Master_State.json")
        if not os.path.exists(master_state_path):
             raise ValueError("Property_Master_State.json not found. Run Phase 3 Synthesis first!")
             
        with open(master_state_path, 'r', encoding='utf-8') as f:
            master_state = json.load(f)
            
        # 2. Collect Approved Room Reports
        approved_rooms = []
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                if file.endswith("_final.json"):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        room_data = json.load(f)
                        # CRITICAL: Surveyor Approval Gate
                        if room_data.get("is_approved") is True:
                            approved_rooms.append(room_data)
                            print(f"[{project_id}] Included Approved Room: {room_data.get('room_name')}")
                        else:
                            print(f"[{project_id}] Skipped Unapproved Room: {room_data.get('room_name')}")

        # 3. Render HTML
        render_data = {
            "project_id": project_id,
            "project_ref": master_state.get("metadata", {}).get("reference_number", "UNKNOWN REF"),
            "client_name": master_state.get("metadata", {}).get("client_name", "UNKNOWN CLIENT"),
            "property_address": master_state.get("metadata", {}).get("property_address", "UNKNOWN ADDRESS"),
            "inspection_date": datetime.now().strftime("%d %B %Y"), # Ideally fetch from session
            "report_date": datetime.now().strftime("%d %B %Y"),
            "executive_summary": master_state.get("executive_summary", "No executive summary generated."),
            "approved_rooms": approved_rooms
        }

        html_content = self.template.render(**render_data)
        html_out_path = os.path.join(self.output_dir, f"{project_id}_draft.html")
        
        with open(html_out_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"[{project_id}] HTML Draft Generated: {os.path.basename(html_out_path)}")

        # 4. Generate PDF using Playwright
        pdf_out_path = os.path.join(self.output_dir, f"{project_id}_Final_RICS.pdf")
        
        try:
            from playwright.async_api import async_playwright
            import urllib.request
            
            # Convert Windows path to purely valid file:// URI
            file_url = 'file://' + urllib.request.pathname2url(os.path.abspath(html_out_path))
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(file_url, wait_until="networkidle")
                await page.pdf(path=pdf_out_path, format="A4", print_background=True, margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"})
                await browser.close()
                
            print(f"[{project_id}] PDF successfully generated: {pdf_out_path}")
            return pdf_out_path
        except Exception as e:
            print(f"[{project_id}] Playwright error: {e}")
            return html_out_path
