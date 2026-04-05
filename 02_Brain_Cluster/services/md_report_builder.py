"""
RICS Markdown Report Builder — Core Engine
Assembles room inspection data into a full RICS Level 3 MD report,
then converts to HTML+CSS → PDF.

Pipeline:
  1. Gather room data from DB/filesystem
  2. Map rooms → RICS elements (via room_element_mapper)
  3. Generate narratives per element (via Gemini)
  4. Assemble into rics_report.md (via Jinja2 skeleton)
  5. Convert MD → HTML → PDF (via PyMuPDF Story API)
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

import fitz  # PyMuPDF
import markdown
from jinja2 import Environment, FileSystemLoader

from services.rics_schema import (
    RICSReport, ProjectInfo, RICSElement, EvidencePhoto,
    SectionA, SectionB, SectionC, SectionH, SectionI, SectionJ,
    SectionK, SectionL, SectionM,
    ConditionRating, ConditionRatingEntry,
    ALL_RICS_ELEMENTS, DOCUMENTS_TO_OBTAIN_MAP
)
from services.room_element_mapper import aggregate_room_data_to_elements

logger = logging.getLogger("rics_report_builder")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CSS_PATH = os.path.join(TEMPLATE_DIR, "rics_style.css")
SKELETON_TEMPLATE = "rics_skeleton.md.j2"


class MdReportBuilder:
    """
    Main engine for building RICS Level 3 reports.
    
    Usage:
        builder = MdReportBuilder(project_id="KMT-123")
        builder.gather_data()              # Load rooms, photos, project info
        builder.map_rooms_to_elements()    # Room data → RICS elements
        await builder.generate_narratives() # Gemini generates per-element text
        builder.compute_section_b()        # Auto-compute condition tables
        md_content = builder.assemble_md() # Build the full Markdown
        pdf_path = builder.generate_pdf()  # MD → HTML → PDF
    """
    
    def __init__(self, project_id: str, storage_base: str = None):
        self.project_id = project_id
        self.storage_base = storage_base or os.path.join(BASE_DIR, "project_data")
        
        # Report data
        self.report = RICSReport(project=ProjectInfo(id=project_id))
        self.elements: Dict[str, RICSElement] = {}
        self.rooms: List[dict] = []
        self.md_content: str = ""
        self.html_content: str = ""
        
        # Jinja2 environment
        self.jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        
        # CSS
        with open(CSS_PATH) as f:
            self.css_content = f.read()
    
    # ============= STEP 1: GATHER DATA =============
    
    def gather_data(self, project_data: dict = None, rooms_data: List[dict] = None):
        """
        Load project info and room data.
        Can be called with explicit data or from filesystem.
        """
        if project_data:
            self.report.project = ProjectInfo(**project_data)
        else:
            self._load_project_from_fs()
        
        if rooms_data:
            self.rooms = rooms_data
        else:
            self._load_rooms_from_fs()
        
        logger.info(f"Gathered data: project={self.report.project.reference}, "
                     f"rooms={len(self.rooms)}")
    
    def _load_project_from_fs(self):
        """Load project info from filesystem (project_data/{id}/)"""
        project_dir = os.path.join(self.storage_base, self.project_id)
        meta_path = os.path.join(project_dir, "project_meta.json")
        
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                data = json.load(f)
            self.report.project = ProjectInfo(**data)
    
    def _load_rooms_from_fs(self):
        """Load room data from filesystem"""
        project_dir = os.path.join(self.storage_base, self.project_id)
        rooms_dir = os.path.join(project_dir, "rooms")
        
        if not os.path.exists(rooms_dir):
            logger.warning(f"No rooms directory: {rooms_dir}")
            return
        
        for fname in sorted(os.listdir(rooms_dir)):
            if fname.endswith(".json"):
                with open(os.path.join(rooms_dir, fname)) as f:
                    room_data = json.load(f)
                self.rooms.append(room_data)
        
        logger.info(f"Loaded {len(self.rooms)} rooms from filesystem")
    
    # ============= STEP 2: MAP ROOMS → ELEMENTS =============
    
    def map_rooms_to_elements(self):
        """Map all room data to RICS elements using keyword + room-type mapping"""
        self.elements = aggregate_room_data_to_elements(self.rooms)
        
        # Convert to lists for sections
        self.report.section_d_elements = [
            e for e in self.elements.values() if e.section == "D"
        ]
        self.report.section_e_elements = [
            e for e in self.elements.values() if e.section == "E"
        ]
        self.report.section_f_elements = [
            e for e in self.elements.values() if e.section == "F"
        ]
        self.report.section_g_elements = [
            e for e in self.elements.values() if e.section == "G"
        ]
        
        # Sort by code
        for lst in [self.report.section_d_elements, self.report.section_e_elements,
                     self.report.section_f_elements, self.report.section_g_elements]:
            lst.sort(key=lambda e: e.code)
        
        logger.info(f"Mapped to elements: D={len(self.report.section_d_elements)}, "
                     f"E={len(self.report.section_e_elements)}, "
                     f"F={len(self.report.section_f_elements)}, "
                     f"G={len(self.report.section_g_elements)}")
    
    # ============= STEP 3: GENERATE NARRATIVES =============
    
    async def generate_narratives(self, gemini_service=None):
        """
        Generate professional RICS narratives for each element using Gemini.
        Auto-initializes GeminiService if available and no service is passed.
        Falls back to raw notes if Gemini is unavailable.
        """
        # Try to auto-initialize Gemini if not provided
        gemini_model = None
        if gemini_service:
            gemini_model = gemini_service
        else:
            try:
                from services.gemini_service import GeminiService
                svc = GeminiService()
                gemini_model = svc.model  # genai.GenerativeModel instance
                logger.info(f"Gemini activated: {svc.MODEL_NAME}")
            except Exception as e:
                logger.warning(f"Gemini unavailable, using fallback: {e}")
        
        for elem in self.report.get_all_elements():
            if not elem.raw_notes and not elem.photos:
                elem.condition_rating = ConditionRating.NI
                elem.narrative = "This element was not accessible or not present at the time of inspection."
                continue
            
            if gemini_model:
                elem.narrative = await self._generate_element_narrative(
                    elem, gemini_model
                )
            else:
                # Fallback: format raw notes professionally
                elem.narrative = self._format_raw_notes(elem)
            
            # If no condition rating set, default to 1
            if elem.condition_rating == ConditionRating.NI and elem.raw_notes:
                elem.condition_rating = ConditionRating.GREEN
        
        logger.info("Narratives generated for all elements")

    # ============= STEP 3b: GENERATE LEGAL/RISK/ACTION SECTIONS =============

    async def generate_legal_sections(self, gemini_service=None):
        """
        Generate smart legal sections H, I, L using Gemini.
        These prompts are designed to PROTECT THE SURVEYOR through:
        - Precise legal language that limits liability
        - Risk-aware disclaimers based on actual property condition
        - Actionable recommendations that demonstrate due diligence
        """
        gemini_model = None
        if gemini_service:
            gemini_model = gemini_service
        else:
            try:
                from services.gemini_service import GeminiService
                svc = GeminiService()
                gemini_model = svc.model
            except Exception as e:
                logger.warning(f"Gemini unavailable for legal sections: {e}")
                return

        # Build property context from condition ratings
        context = self._build_property_context()

        # Generate H, I, L in parallel
        import asyncio
        h_task = self._generate_section_h(gemini_model, context)
        i_task = self._generate_section_i(gemini_model, context)
        l_task = self._generate_section_l(gemini_model, context)

        results = await asyncio.gather(h_task, i_task, l_task, return_exceptions=True)

        if not isinstance(results[0], Exception):
            self.report.section_h = results[0]
        if not isinstance(results[1], Exception):
            self.report.section_i = results[1]
        if not isinstance(results[2], Exception):
            self.report.section_l = results[2]

        logger.info("Legal sections H, I, L generated")

    def _build_property_context(self) -> str:
        """Build rich context for Gemini legal prompts from all inspection data."""
        lines = []
        lines.append(f"Property: {self.report.project.address}")
        lines.append(f"Type: {self.report.section_c.property_type}")
        lines.append(f"Year built: {self.report.section_c.year_built}")
        lines.append(f"Construction: {self.report.section_c.construction}")
        lines.append(f"Tenure: {self.report.section_c.tenure}")
        lines.append(f"Listed building: {self.report.section_c.listed_building}")
        lines.append("")

        # Elements with condition ratings
        for elem in self.report.get_all_elements():
            cr = {1: "GREEN(1)", 2: "AMBER(2)", 3: "RED(3)", 0: "NI"}.get(elem.condition_rating.value, "NI")
            note = elem.narrative[:200] if elem.narrative else "No notes"
            lines.append(f"  [{cr}] {elem.code} {elem.name}: {note}")

        return "\n".join(lines)

    async def _generate_section_h(self, gemini_model, context: str) -> SectionH:
        """Generate Section H — Issues for Legal Advisers.
        RICS-compliant, protective of surveyor, property-specific."""
        prompt = f"""You are a senior RICS Chartered Surveyor (FRICS) with 25+ years experience
writing Level 3 Home Survey reports. You have extensive knowledge of:
- Defective Premises Act 1972 (as amended 2023)
- Building Safety Act 2022
- Party Wall etc Act 1996
- Housing Act 2004 (HHSRS)
- Environmental Protection Act 1990
- Town and Country Planning Act 1990
- Listed Buildings and Conservation Areas Act 1990

Write Section H: "Issues for your legal advisers" for this property.

PROPERTY INSPECTION DATA:
{context}

RULES:
1. Start with standard disclaimer: "We are not legally qualified, and we strongly recommend
that you obtain independent legal advice before committing to this purchase."
2. Identify ALL legal issues arising from the inspection findings:
   - Boundary disputes (if external walls/fences show evidence)
   - Party wall matters (shared walls, loft conversions)
   - Planning permission concerns (extensions, conversions, alterations)
   - Building regulations compliance (any works noted)
   - Environmental issues (asbestos, flooding, contamination)
   - Rights of way, easements, covenants
   - Insurance claims history if damage noted
   - Leasehold/freehold issues
3. For each issue, explain WHY it is flagged based on specific inspection evidence
4. Use formal British English, professional but accessible
5. Each paragraph should start with the topic in BOLD
6. Include specific references to relevant legislation
7. PROTECT THE SURVEYOR: use careful qualifying language
   ("it appears", "we recommend verification", "legal advice should be sought")

Write 400-800 words. Be thorough but not alarmist."""

        try:
            import asyncio
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    gemini_model.generate_content,
                    prompt
                ),
                timeout=45.0
            )
            return SectionH(narrative=response.text)
        except Exception as e:
            logger.error(f"Section H generation failed: {e}")
            return SectionH(narrative=(
                'We are not legally qualified, and we strongly recommend '
                'that you obtain independent legal advice before committing '
                'to this purchase. Please refer to the specific condition '
                'ratings and observations throughout this report for items '
                'that may have legal implications.'
            ))

    async def _generate_section_i(self, gemini_model, context: str) -> SectionI:
        """Generate Section I — Risks.
        Comprehensive risk assessment based on actual findings."""
        prompt = f"""You are a senior RICS Chartered Surveyor (FRICS) specialising in
building pathology and risk assessment. Write Section I: "Risks" for this property.

PROPERTY INSPECTION DATA:
{context}

Cover ALL applicable risk categories:

1. **Asbestos** — Was the property built before 2000? Note that asbestos-containing
   materials (ACMs) may be present in artex coatings, floor tiles, pipe lagging,
   roofing materials, etc. Reference HSE guidance HSG264.

2. **Flooding** — Any signs of water ingress, proximity to watercourses,
   basement/cellar conditions. Reference EA flood maps.

3. **Subsidence / Settlement** — Cracking patterns, tree proximity,
   clay soils, historical mining activity.

4. **Radon** — Geographic radon risk based on property location.
   Reference PHE/UKHSA radon maps.

5. **Japanese Knotweed** — Any invasive species noted in grounds.
   Reference Environment Agency guidance.

6. **Fire Safety** — Escape routes, smoke/CO detectors, fire doors,
   compartmentation in converted properties.

7. **Damp and Timber** — Rising/penetrating damp, condensation, woodworm,
   wet/dry rot evidence.

8. **Electrical Safety** — Age of installation, consumer unit type,
   reference BS 7671.

9. **Structural Stability** — Load-bearing wall concerns, roof structure
   adequacy, foundation issues.

For each risk:
- State whether it is HIGH / MEDIUM / LOW based on evidence
- Reference the specific element code where evidence was found
- Recommend specialist investigation where appropriate
- Use protective language for the surveyor

Respond with JSON:
{{{{
  "narrative": "... full formatted narrative (500-800 words) ...",
  "asbestos_risk": true/false,
  "flood_risk": true/false,
  "subsidence_risk": true/false,
  "radon_risk": true/false,
  "japanese_knotweed": true/false
}}}}"""

        try:
            import asyncio
            import google.generativeai as genai
            config = genai.GenerationConfig(
                temperature=0.15,
                candidate_count=1,
                response_mime_type="application/json"
            )
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    gemini_model.generate_content,
                    prompt,
                    generation_config=config
                ),
                timeout=45.0
            )
            data = json.loads(response.text)
            return SectionI(
                narrative=data.get("narrative", ""),
                asbestos_risk=data.get("asbestos_risk", False),
                flood_risk=data.get("flood_risk", False),
                subsidence_risk=data.get("subsidence_risk", False),
                radon_risk=data.get("radon_risk", False),
                japanese_knotweed=data.get("japanese_knotweed", False),
            )
        except Exception as e:
            logger.error(f"Section I generation failed: {e}")
            return SectionI(narrative=(
                'A full risk assessment should be carried out by a '
                'qualified specialist. Please refer to the condition '
                'ratings throughout this report for identified risk areas.'
            ))

    async def _generate_section_l(self, gemini_model, context: str) -> SectionL:
        """Generate Section L — What to do now.
        Smart action plan that protects the surveyor through due diligence."""
        prompt = f"""You are a senior RICS Chartered Surveyor (FRICS) writing the
"What to do now" section of a Level 3 Home Survey. This section is CRITICAL
as it provides the client with a prioritised action plan.

PROPERTY INSPECTION DATA:
{context}

Generate a structured action plan with 4 categories:

1. **urgent_actions** — Items requiring IMMEDIATE attention (within 7 days).
   These should match elements with Condition Rating 3 (RED).
   Include: what needs doing, why it's urgent, who to contact.

2. **pre_purchase_actions** — Steps to take BEFORE exchange of contracts.
   Include: specialist reports needed, cost estimates to obtain,
   negotiations to have with vendor.

3. **ongoing_maintenance** — Regular maintenance recommendations.
   Include: annual/seasonal tasks, typical costs, prevention measures.

4. **professional_referrals** — Specialists to instruct.
   Include: type of specialist, what they should assess, approximate cost.

IMPORTANT SURVEYOR PROTECTION RULES:
- Each action must reference the specific element code (e.g. "D2 Roof coverings")
- Use language that demonstrates the surveyor has fulfilled their duty of care
- Include cost guidance ranges where possible (e.g. "£500—£1,500")
- Note where delay could lead to further deterioration
- Flag health and safety concerns prominently

Also write a brief narrative introduction (2-3 sentences) summarising
the overall urgency level of this property.

Respond with JSON:
{{{{
  "narrative": "Based on our inspection...",
  "urgent_actions": ["...", "..."],
  "pre_purchase_actions": ["...", "..."],
  "ongoing_maintenance": ["...", "..."],
  "professional_referrals": ["...", "..."]
}}}}"""

        try:
            import asyncio
            import google.generativeai as genai
            config = genai.GenerationConfig(
                temperature=0.2,
                candidate_count=1,
                response_mime_type="application/json"
            )
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    gemini_model.generate_content,
                    prompt,
                    generation_config=config
                ),
                timeout=45.0
            )
            data = json.loads(response.text)
            return SectionL(
                narrative=data.get("narrative", ""),
                urgent_actions=data.get("urgent_actions", []),
                pre_purchase_actions=data.get("pre_purchase_actions", []),
                ongoing_maintenance=data.get("ongoing_maintenance", []),
                professional_referrals=data.get("professional_referrals", []),
            )
        except Exception as e:
            logger.error(f"Section L generation failed: {e}")
            return SectionL(
                narrative=(
                    'Based on our inspection, we recommend taking the '
                    'actions listed below. Please prioritise items '
                    'identified as urgent.'
                ),
                urgent_actions=[],
                pre_purchase_actions=['Obtain all recommended specialist reports before exchange of contracts.'],
                ongoing_maintenance=['Establish a programme of regular maintenance and annual inspections.'],
                professional_referrals=[],
            )
    
    async def _generate_element_narrative(
        self, element: RICSElement, gemini_model
    ) -> str:
        """Generate Gemini narrative for one element using genai directly.
        Timeout: 30 seconds per element — falls back to raw notes on timeout."""
        prompt = f"""You are an expert RICS Chartered Surveyor writing a Level 3 Home Survey report.

Write a professional narrative for element **{element.code} {element.name}**.

The narrative should:
- Be written in British English, formal professional tone
- Include BRE/BSI references where appropriate
- Describe the current condition
- Note any defects or concerns
- Provide maintenance recommendations
- Be 2-5 paragraphs long

Raw inspection notes from the surveyor:
{chr(10).join(element.raw_notes)}

Rooms inspected: {', '.join(element.source_rooms)}
{f"Damp readings: {element.damp_readings}" if element.damp_readings else ""}

Also determine the condition rating:
- 1 (Green): No repair currently needed
- 2 (Amber): Defects that need repairing but not urgent  
- 3 (Red): Serious/urgent defects

Respond with JSON:
{{"narrative": "...", "condition_rating": 1|2|3, "repair_urgency": "urgent|within_12_months|planned_maintenance|monitor|none"}}"""

        try:
            import asyncio
            import google.generativeai as genai
            config = genai.GenerationConfig(
                temperature=0.2,
                candidate_count=1,
                response_mime_type="application/json"
            )
            # Timeout: 30 seconds per element to prevent hanging
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    gemini_model.generate_content,
                    prompt,
                    generation_config=config
                ),
                timeout=30.0
            )
            data = json.loads(response.text)
            element.condition_rating = ConditionRating(data.get("condition_rating", 1))
            return data.get("narrative", "")
        except asyncio.TimeoutError:
            logger.warning(f"Gemini TIMEOUT (30s) for {element.code} {element.name}, using fallback")
            return self._format_raw_notes(element)
        except Exception as e:
            logger.error(f"Gemini narrative error for {element.code}: {e}")
            return self._format_raw_notes(element)
    
    def _format_raw_notes(self, element: RICSElement) -> str:
        """Format raw notes into a readable narrative (fallback)"""
        if not element.raw_notes:
            return f"No significant observations were noted for {element.name} at the time of inspection."
        
        notes_text = "\n\n".join(element.raw_notes)
        rooms = ", ".join(element.source_rooms) if element.source_rooms else "the property"
        
        return (
            f"During the inspection of {rooms}, the following was noted regarding "
            f"{element.name.lower()}:\n\n{notes_text}"
        )
    
    # ============= STEP 4: COMPUTE SECTION B =============
    
    def compute_section_b(self):
        """Auto-compute condition ratings table and documents to obtain"""
        ratings = self.report.compute_condition_ratings()
        self.report.section_b.condition_ratings_urgent = ratings["urgent"]
        self.report.section_b.condition_ratings_attention = ratings["attention"]
        self.report.section_b.condition_ratings_ok = ratings["ok"]
        self.report.section_b.condition_ratings_not_inspected = ratings["not_inspected"]
        
        self.report.section_b.documents_to_obtain = self.report.compute_documents_to_obtain()
        
        logger.info(f"Section B computed: urgent={len(ratings['urgent'])}, "
                     f"attention={len(ratings['attention'])}, ok={len(ratings['ok'])}")
    
    # ============= CONDITION RATING NORMALIZER =============
    
    CR_MAP = {
        0: {"label": "NI", "css": "ni", "display": "Not inspected"},
        1: {"label": "CR1", "css": "1", "display": "CR1 — No significant defects"},
        2: {"label": "CR2", "css": "2", "display": "CR2 — Defects that need repairing"},
        3: {"label": "CR3", "css": "3", "display": "CR3 — Urgent repairs needed"},
    }
    
    # Photo Intelligence manifest (element_code -> list of AnnotatedPhoto dicts)
    _photo_manifest: dict = {}
    
    def set_photo_manifest(self, manifest: dict):
        """Set the photo intelligence manifest from PhotoIntelligence.run()"""
        self._photo_manifest = manifest or {}
        logger.info(f"Photo manifest loaded: {sum(len(v) for v in self._photo_manifest.values())} photos across {len(self._photo_manifest)} elements")
    
    def _normalize_element(self, elem_dict: dict) -> dict:
        """Convert condition_rating integer to template-friendly values
        and attach evidence_photos from photo intelligence manifest."""
        cr_val = elem_dict.get("condition_rating", 0)
        cr_info = self.CR_MAP.get(cr_val, self.CR_MAP[0])
        elem_dict["cr_label"] = cr_info["label"]
        elem_dict["cr_css"] = cr_info["css"]
        elem_dict["cr_display"] = cr_info["display"]
        
        # Attach evidence_photos from photo intelligence manifest
        element_code = elem_dict.get("code", "")
        if element_code and element_code in self._photo_manifest:
            elem_dict["evidence_photos"] = self._photo_manifest[element_code]
            logger.debug(f"Attached {len(elem_dict['evidence_photos'])} evidence photos to {element_code}")
        
        return elem_dict
    
    # ============= STEP 5: ASSEMBLE MD =============
    
    def assemble_md(self, photo_manifest: dict = None) -> str:
        """Assemble the full Markdown report from all sections.
        
        Args:
            photo_manifest: Optional dict from PhotoIntelligence.run()
                           mapping element_code -> list of AnnotatedPhoto dicts
        """
        # Set photo manifest if provided
        if photo_manifest:
            self.set_photo_manifest(photo_manifest)
        
        # Assign photo numbers
        self.report.assign_photo_numbers()
        
        # Build template data
        template_data = {
            "project": self.report.project.model_dump(),
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
            "version": self.report.version,
            "section_a": self.report.section_a.model_dump(),
            "section_b": self.report.section_b.model_dump(),
            "section_c": self.report.section_c.model_dump(),
            "condition_ratings": {
                "urgent": [r.model_dump() for r in self.report.section_b.condition_ratings_urgent],
                "attention": [r.model_dump() for r in self.report.section_b.condition_ratings_attention],
                "ok": [r.model_dump() for r in self.report.section_b.condition_ratings_ok],
                "not_inspected": [r.model_dump() for r in self.report.section_b.condition_ratings_not_inspected],
            },
            "section_d_elements": [self._normalize_element(e.model_dump()) for e in self.report.section_d_elements],
            "section_e_elements": [self._normalize_element(e.model_dump()) for e in self.report.section_e_elements],
            "section_f_elements": [self._normalize_element(e.model_dump()) for e in self.report.section_f_elements],
            "section_g_elements": [self._normalize_element(e.model_dump()) for e in self.report.section_g_elements],
            "section_h": self.report.section_h.model_dump(),
            "section_i": self.report.section_i.model_dump(),
            "section_j": self.report.section_j.model_dump(),
            "section_k": self.report.section_k.model_dump(),
            "section_l": self.report.section_l.model_dump(),
            "section_m": self.report.section_m.model_dump(),
            "photo_index": self._build_photo_index(),
        }
        
        template = self.jinja_env.get_template(SKELETON_TEMPLATE)
        self.md_content = template.render(**template_data)
        
        logger.info(f"Assembled MD report: {len(self.md_content)} chars")
        return self.md_content
    
    def _build_photo_index(self) -> dict:
        """Group all photos by section for the Photo Index"""
        index = {}
        section_names = {
            "A": "A About the inspection",
            "B": "B Overall opinion",
            "C": "C About the property",
            "D": "D Outside the property",
            "E": "E Inside the property",
            "F": "F Services",
            "G": "G Grounds",
        }
        
        for photo in self.report.all_photos:
            section = photo.section_code or "Other"
            section_label = section_names.get(section, section)
            if section_label not in index:
                index[section_label] = []
            index[section_label].append(photo.model_dump())
        
        return index
    
    # ============= STEP 6: GENERATE PDF =============
    
    def generate_pdf(self, output_path: str = None) -> str:
        """Convert MD → HTML → PDF via subprocess-isolated PyMuPDF.
        
        MuPDF can segfault on complex CSS, which kills the entire process.
        We isolate it in a subprocess so crashes don't kill uvicorn.
        """
        import subprocess
        
        if not self.md_content:
            self.assemble_md()
        
        # Strip YAML frontmatter (---...---) before MD conversion
        # This metadata is already shown in the cover page HTML
        import re
        clean_md = re.sub(r'^---\s*\n.*?\n---\s*\n', '', self.md_content, flags=re.DOTALL)
        
        # MD → HTML
        html_body = markdown.markdown(
            clean_md,
            extensions=['tables', 'fenced_code', 'toc']
        )
        
        self.html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{self.css_content}</style></head>
<body>{html_body}</body>
</html>"""
        
        # Determine output path
        if not output_path:
            out_dir = os.path.join(self.storage_base, self.project_id, "reports")
            os.makedirs(out_dir, exist_ok=True)
            output_path = os.path.join(
                out_dir,
                f"RICS_Report_{self.report.version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save HTML to temp file for subprocess
        html_path = output_path.replace(".pdf", ".html")
        with open(html_path, "w") as f:
            f.write(self.html_content)
        
        # Run PDF generation in isolated subprocess
        generator_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "pdf_generator.py"
        )
        
        try:
            result = subprocess.run(
                ["python3", generator_script, html_path, output_path,
                 self.report.project.reference],
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode == 0 and result.stdout.startswith("OK|"):
                parts = result.stdout.strip().split("|")
                page_count = int(parts[1])
                pdf_size = int(parts[2])
                logger.info(f"PDF generated: {output_path} ({page_count} pages, {pdf_size}KB)")
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                logger.error(f"PDF subprocess failed (exit {result.returncode}): {error_msg[:500]}")
                # Return HTML path as fallback
                logger.info(f"HTML saved as fallback: {html_path}")
                return html_path
                
        except subprocess.TimeoutExpired:
            logger.error("PDF generation timed out (120s)")
            return html_path
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return html_path
        
        return output_path
    
    # ============= UTILITY METHODS =============
    
    def get_md_content(self) -> str:
        """Return the current MD content"""
        return self.md_content
    
    def update_md_content(self, new_content: str):
        """Update MD content (for voice/mobile/web editing)"""
        self.md_content = new_content
    
    def update_section(self, section_code: str, content: str):
        """Update a specific section's narrative in the MD"""
        # Find the section marker and replace content
        marker_start = f'data-code="{section_code}"'
        marker_end = "---"
        
        if marker_start in self.md_content:
            parts = self.md_content.split(marker_start)
            if len(parts) >= 2:
                after_marker = parts[1]
                # Find the narrative area and replace
                # This is a simplified approach; voice editor will use Gemini for precision
                logger.info(f"Section {section_code} updated")
    
    def save_md(self, path: str = None) -> str:
        """Save the current MD to a file"""
        if not path:
            out_dir = os.path.join(self.storage_base, self.project_id, "reports")
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"rics_report_{self.report.version}.md")
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(self.md_content)
        
        return path
    
    def save_html(self, path: str = None) -> str:
        """Save the current HTML to a file"""
        if not path:
            out_dir = os.path.join(self.storage_base, self.project_id, "reports")
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"rics_report_{self.report.version}.html")
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(self.html_content)
        
        return path
