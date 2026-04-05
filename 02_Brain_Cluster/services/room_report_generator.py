import os
import json
import google.generativeai as genai 
from jinja2 import Environment, FileSystemLoader
from .storage_service import get_storage_service

class RoomReportGenerator:
    def __init__(self):
        self.storage = get_storage_service()
        self.model_name = os.environ.get("GEMINI_MODEL_KEY", "gemini-3-flash-preview")
        
        # Load Jinja2 Template
        template_dir = os.path.join(os.path.dirname(__file__), "..", "prompts", "templates", "rics")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template("room_report_generation.j2")

    async def generate_rics_narrative(self, project_id: str, room_id: str) -> dict:
        """
        1. Locates the raw JSON for a given room.
        2. Pipes it to Gemini via the RICS Jinja2 prompt.
        3. Saves the synthesized output to `[room_id]_final.json`.
        """
        print(f"[{room_id}] Starting AI RICS Narrative Generation...")
        
        # 1. Locate the Project Context
        from .synthesis_engine import _resolve_project_semantic_path
        project_dir = await _resolve_project_semantic_path(project_id)
        if not project_dir:
            raise ValueError(f"Project directory not found for {project_id}")

        # Note: We assume the latest session for now, or just search all sessions for the room
        # For robustness in Phase 4, we'll scan project_dir to find the room
        room_filepath = None
        for root, dirs, files in os.walk(project_dir):
            if f"{room_id}.json" in files:
                room_filepath = os.path.join(root, f"{room_id}.json")
                break
                
        if not room_filepath:
            raise ValueError(f"Room JSON '{room_id}.json' not found in project {project_id}")

        # 2. Load Raw Room Data
        with open(room_filepath, 'r', encoding='utf-8') as f:
            raw_room_data = json.load(f)

        # 3. Render Prompt
        prompt = self.template.render(
            room_data=json.dumps(raw_room_data, indent=2),
            room_name_placeholder=raw_room_data.get("room_name", "Unknown Room")
        )

        # 4. Call Gemini (using structured JSON output)
        print(f"[{room_id}] Sending data to Gemini...")
        
        genai.configure() # Auto-loads from env
        model = genai.GenerativeModel(
            self.model_name,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        response = model.generate_content(prompt)

        # 5. Parse and Save Output
        try:
            generated_json = json.loads(response.text)
            
            # Create the final payload including approval status
            final_payload = {
                "room_id": room_id,
                "room_name": generated_json.get("room_name", "Unknown Room"),
                "rics_narrative": generated_json.get("rics_narrative", ""),
                "is_approved": False, # Requires human gate!
                "selected_photos": [], # To be populated by human
                "raw_data_reference": room_filepath
            }
            
            # Save it next to the original file
            final_filepath = room_filepath.replace(".json", "_final.json")
            with open(final_filepath, 'w', encoding='utf-8') as f:
                json.dump(final_payload, f, indent=4)
                
            print(f"[{room_id}] RICS Narrative Generated and saved to {os.path.basename(final_filepath)}")
            return final_payload
            
        except json.JSONDecodeError:
            print(f"[{room_id}] Failed to parse Gemini output as JSON.")
            print(response.text)
            raise ValueError("Gemini returned invalid JSON structure.")
