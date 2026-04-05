"""
RICS Reporting Engine (Strict A-M)
Maps session data to RICS Standard Sections.
"""
import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

class RICSReportEngine:
    def __init__(self, template_dir="reporting/templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.output_dir = "reporting/generated/rics"
        os.makedirs(self.output_dir, exist_ok=True)

    def map_room_to_sections(self, room_data, analysis):
        """
        CONTEXT-AWARE MAPPING LOGIC:
        Determines which RICS sections are active based on the Room Context.
        
        Logic Matrix:
        - Dry Room (Bedroom, Living) -> Section E (Walls, Ceilings, Floors)
        - Wet Room (Kitchen, Bath)   -> Section E + Section F (Plumbing, Ventilation)
        - Services (Utility Room)    -> Section F (Elec, Gas, Water)
        - Exterior (Garden)          -> Section D (Outside) + Section G (Grounds)
        """
        context = room_data.get('context', 'Dry')
        
        # 1. Initialize Flags (All Hidden by default)
        section_flags = {
            "show_a": True, # Always show header
            "show_d": False,
            "show_e": False,
            "show_f": False,
            "show_g": False
        }
        
        # 2. Logic Gate: Enable Sections based on Context
        if context in ["Dry", "General"]:
            section_flags["show_e"] = True
            
        elif context == "Wet":
            section_flags["show_e"] = True
            section_flags["show_f"] = True # For plumbing/water
            
        elif context == "Services":
            section_flags["show_f"] = True
            section_flags["show_e"] = True # Often has walls/ceilings too
            
        elif context == "Exterior":
            section_flags["show_d"] = True
            section_flags["show_g"] = True

        # 3. Map Content to Data Slots
        sections_data = {
            "e_ceilings": None,
            "e_walls": None,
            "e_floors": None, 
            "f_water": None,
            "f_electricity": None
        }

        # --- Section E Mapping ---
        if section_flags["show_e"]:
            summary = analysis.get("summary", "")
            
            # E1 Roof (Internal view)
            if "roof" in summary.lower() or "loft" in summary.lower():
                 pass # Add logic if needed
                 
            # E2 Ceilings (Always strictly mapped for rooms)
            sections_data["e_ceilings"] = {
                 "rating": analysis.get("rating", 1),
                 "description": f"Observation: {summary}",
                 "photos": [f"/media/demo_session/{room_data['id']}/{p}" for p in analysis.get("evidence_photos", [])]
            }
            
            # E3 Walls
            sections_data["e_walls"] = {
                "rating": 1, 
                "description": "Walls appear visually sound unless noted otherwise.",
                "photos": []
            } # Default safe state

        # --- Section F Mapping ---
        if section_flags["show_f"]:
            # Simple heuristic for demo
            sections_data["f_water"] = {
                "rating": analysis.get("rating", 1) if context == "Wet" else 1,
                "description": "Visual inspection of plumbing fixtures."
            }
            
        return {**section_flags, **sections_data}

    def generate_report(self, session_data, mapped_data):
        template = self.env.get_template("rics/master_layout.html")
        
        render_data = {
            "property_address": session_data.get("address", "Unknown Property"),
            "inspection_date": datetime.now().strftime("%d %B %Y"),
            **mapped_data 
        }
        
        return template.render(**render_data)

    def aggregate_session_to_rics(self, session_json):
        """
        Transforms a full session JSON (hierarchical) into RICS sections.
        """
        aggregated = {
            "show_a": True, "show_e": True, "show_f": True,
            "e_ceilings_list": [],
            "e_walls_list": [],
            "f_water_list": []
        }
        
        reports = session_json.get("reports", {})
        for r_id, r_report in reports.items():
            elements = r_report.get("analysis", {}).get("elements", [])
            for elem in elements:
                finding = {
                    "room_name": r_report.get("room_name", r_id),
                    "rating": elem.get("condition_assessment", {}).get("rating", 1),
                    "description": elem.get("condition_assessment", {}).get("condition_description", ""),
                    "photos": [] 
                }
                
                name = elem.get("name", "")
                if name == "Ceilings":
                    aggregated["e_ceilings_list"].append(finding)
                elif "Walls" in name:
                    aggregated["e_walls_list"].append(finding)
                elif name in ["Heating", "Electricity"]:
                    aggregated["f_water_list"].append(finding)
                    
        return aggregated

# Singleton
engine = RICSReportEngine()
