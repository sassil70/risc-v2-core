import fitz  # PyMuPDF
import os
import json
import logging

logger = logging.getLogger(__name__)

# Constants bridging semantic data back to the physical page space
# A4 size is roughly 595 x 842 points (72 points per inch)

COORDS_MAP = {
    'D1  Chimney stacks': {'estimated_start_y': 306.32, 'page': 17},
    'D2  Roof coverings': {'estimated_start_y': 463.64, 'page': 17},
    'D3  Rainwater pipes and gutters': {'estimated_start_y': 620.96, 'page': 17},
    'F1  Electricity': {'estimated_start_y': 306.45, 'page': 25},
    'F2  Gas/oil': {'estimated_start_y': 520.41, 'page': 25},
    'F3  Water': {'estimated_start_y': 183.08, 'page': 26},
    'F4  Heating': {'estimated_start_y': 296.73, 'page': 26},
    'F5  Water heating': {'estimated_start_y': 421.16, 'page': 26}
}

def stamp_rics_report(project_id: str, project_dir: str) -> str:
    """
    Takes the synthesised Property_Master_State.json and the approved Room JSONs,
    and stamps their contents perfectly onto the 51-page T.pdf template.
    """
    try:
        # 1. Locate the Template inside the Reporter Cluster
        template_path = os.path.join(os.path.dirname(__file__), "..", "..", "03_Reporter_Cluster", "assets", "reference_templates", "T.pdf")
        template_path = os.path.abspath(template_path)
        if not os.path.exists(template_path):
            logger.error(f"Critical Error: Template T.pdf not found at {template_path}")
            return None

        # 2. Open the immutable template
        doc = fitz.open(template_path)

        # 3. Read Master State Data
        master_state_path = os.path.join(project_dir, "Property_Master_State.json")
        master_state = {}
        if os.path.exists(master_state_path):
            with open(master_state_path, 'r', encoding='utf-8') as f:
                master_state = json.load(f)

        # 4. Stamp Cover Page Variables
        # Example coordinates - these will need perfect calibration
        cover_page = doc[0] 
        ref_number = master_state.get("metadata", {}).get("reference_number", "UNKNOWN REF")
        
        # Insert text (Requires a defined font, size, x/y coords)
        # cover_page.insert_text(fitz.Point(300, 400), f"Ref: {ref_number}", fontsize=14, color=(0, 0, 0))
        
        # 5. Locate Approved Room Images and Stamp Them
        approved_rooms = []
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                if file.endswith("_final.json"):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        r_data = json.load(f)
                        if r_data.get("is_approved"):
                            approved_rooms.append(r_data)

        # Heuristic Router: Map broad room names to literal RICS COORDS
        def _get_mapped_coords(room_name):
            r_lower = room_name.lower()
            if "ceiling" in r_lower: return COORDS_MAP.get("E1  Ceilings")
            if "wall" in r_lower: return COORDS_MAP.get("E2  Walls and partitions")
            if "floor" in r_lower: return COORDS_MAP.get("E3  Floors")
            if "door" in r_lower: return COORDS_MAP.get("E4  Internal doors")
            if "roof" in r_lower: return COORDS_MAP.get("D2  Roof coverings")
            if "electric" in r_lower: return COORDS_MAP.get("F1  Electricity")
            if "heat" in r_lower: return COORDS_MAP.get("F4  Heating")
            return None # Unmapped generic room

        for room in approved_rooms:
            coords = _get_mapped_coords(room.get('room_name', ''))
            if not coords:
                continue
                
            page = doc[coords['page']]
            start_y = coords['estimated_start_y']
            
            # 1. Stamp Text
            narrative = room.get('ai_room_narrative', 'Narrative omitted.')
            text_rect = fitz.Rect(80, start_y, 500, start_y + 150)
            
            # Use insert_textbox to allow auto-wrapping of the AI narrative
            page.insert_textbox(
                text_rect, 
                f"{room.get('room_name', 'Room')} ({room.get('floor_name', 'Floor')}): {narrative}", 
                fontsize=10, 
                color=(0, 0, 0.4) # Slightly blue to differentiate from template
            )
            
            # 2. Stamp Images (Up to 3 across)
            images = room.get('selected_diagnostic_images', [])
            img_start_y = start_y + 160
            img_size = 120
            
            for i, img_path in enumerate(images):
                if os.path.exists(img_path):
                    x_pos = 80 + (i * (img_size + 20))
                    rect = fitz.Rect(x_pos, img_start_y, x_pos + img_size, img_start_y + img_size)
                    page.insert_image(rect, filename=img_path)

        # 6. Output the Final PDF
        output_path = os.path.join(project_dir, "RICS_Final_Report.pdf")
        
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        
        return output_path

    except Exception as e:
        logger.error(f"Failed to execute PDF Stamping: {e}")
        return None
