"""
RICS Level 3 Report — Pydantic Schema
Represents every section, element, and field in a RICS Home Survey Level 3.
Derived from analysis of 8 real reports (310-456 pages each).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import date


# ============= ENUMS =============

class ConditionRating(int, Enum):
    """RICS Condition Rating Scale"""
    GREEN = 1   # No repair currently needed
    AMBER = 2   # Defects that need repairing but not urgent
    RED = 3     # Serious/urgent defects
    NI = 0      # Not inspected


class RepairUrgency(str, Enum):
    URGENT = "urgent"
    SOON = "within_12_months"
    PLANNED = "planned_maintenance"
    MONITOR = "monitor"
    NONE = "none"


# ============= PHOTO =============

class EvidencePhoto(BaseModel):
    """A photo taken during inspection"""
    photo_id: str
    path: str                                       # Local file path
    global_number: Optional[int] = None             # Sequential number in full report (1..N)
    caption: Optional[str] = None
    date: Optional[str] = None                      # Date photo was taken
    section_code: Optional[str] = None              # Which RICS section (D, E, F...)
    element_code: Optional[str] = None              # Which element (D1, E2...)
    room_id: Optional[str] = None                   # Which room it was taken in


# ============= RICS ELEMENT =============

class RICSElement(BaseModel):
    """One inspectable element (D1 Chimney stacks, E2 Ceilings, etc.)"""
    code: str                                       # e.g. "D1", "E2", "F3"
    name: str                                       # e.g. "Chimney stacks"
    section: str                                    # "D", "E", "F", "G"
    condition_rating: ConditionRating = ConditionRating.NI
    narrative: str = ""                             # AI-generated professional narrative
    repair_urgency: RepairUrgency = RepairUrgency.NONE
    repair_cost_estimate: Optional[str] = None      # e.g. "£500-£1,500"
    photos: List[EvidencePhoto] = Field(default_factory=list)
    cross_refs: List[str] = Field(default_factory=list)   # e.g. ["H — Party wall"]
    source_rooms: List[str] = Field(default_factory=list) # Room IDs this element draws from
    raw_notes: List[str] = Field(default_factory=list)    # Original surveyor notes
    damp_readings: Optional[Dict[str, float]] = None      # Moisture readings if any


# ============= STANDARD RICS ELEMENTS =============

RICS_ELEMENTS_D = [
    {"code": "D1", "name": "Chimney stacks", "section": "D"},
    {"code": "D2", "name": "Roof coverings", "section": "D"},
    {"code": "D3", "name": "Rainwater pipes and gutters", "section": "D"},
    {"code": "D4", "name": "Main walls", "section": "D"},
    {"code": "D5", "name": "Windows", "section": "D"},
    {"code": "D6", "name": "Outside doors (including patio doors)", "section": "D"},
    {"code": "D7", "name": "Conservatory and porches", "section": "D"},
    {"code": "D8", "name": "Other joinery and finishes", "section": "D"},
    {"code": "D9", "name": "Other", "section": "D"},
]

RICS_ELEMENTS_E = [
    {"code": "E1", "name": "Roof structure", "section": "E"},
    {"code": "E2", "name": "Ceilings", "section": "E"},
    {"code": "E3", "name": "Walls and partitions", "section": "E"},
    {"code": "E4", "name": "Floors", "section": "E"},
    {"code": "E5", "name": "Fireplaces, chimney breasts and flues", "section": "E"},
    {"code": "E6", "name": "Built-in fittings", "section": "E"},
    {"code": "E7", "name": "Woodwork (e.g. staircase joinery)", "section": "E"},
    {"code": "E8", "name": "Bathroom fittings", "section": "E"},
    {"code": "E9", "name": "Other", "section": "E"},
]

RICS_ELEMENTS_F = [
    {"code": "F1", "name": "Electricity", "section": "F"},
    {"code": "F2", "name": "Gas/oil", "section": "F"},
    {"code": "F3", "name": "Water", "section": "F"},
    {"code": "F4", "name": "Heating", "section": "F"},
    {"code": "F5", "name": "Water heating", "section": "F"},
    {"code": "F6", "name": "Drainage", "section": "F"},
]

RICS_ELEMENTS_G = [
    {"code": "G1", "name": "Garage", "section": "G"},
    {"code": "G2", "name": "Permanent outbuildings and other structures", "section": "G"},
    {"code": "G3", "name": "Outside areas and boundaries", "section": "G"},
    {"code": "G4", "name": "Trees", "section": "G"},
    {"code": "G5", "name": "Other (grounds)", "section": "G"},
]

ALL_RICS_ELEMENTS = RICS_ELEMENTS_D + RICS_ELEMENTS_E + RICS_ELEMENTS_F + RICS_ELEMENTS_G


# ============= SECTION MODELS =============

class SectionA(BaseModel):
    """A — About the Inspection"""
    intro: str = "This RICS Home Survey – Level 3 has been produced by a surveyor."
    weather: str = ""
    property_status: str = ""
    restrictions: str = ""
    
    
class ConditionRatingEntry(BaseModel):
    """One row in the Condition Ratings table"""
    code: str
    name: str
    comment: str = ""


class SectionB(BaseModel):
    """B — Overall Opinion"""
    overall_narrative: str = ""
    condition_ratings_urgent: List[ConditionRatingEntry] = Field(default_factory=list)
    condition_ratings_attention: List[ConditionRatingEntry] = Field(default_factory=list)
    condition_ratings_ok: List[ConditionRatingEntry] = Field(default_factory=list)
    condition_ratings_not_inspected: List[ConditionRatingEntry] = Field(default_factory=list)
    documents_to_obtain: List[str] = Field(default_factory=list)
    further_investigations: str = ""
    repair_summary: str = ""
    cost_guidance: Optional[str] = None


DOCUMENTS_TO_OBTAIN_MAP = {
    "F1": "ELECTRICAL TESTING CERTIFICATION (EICR)",
    "F2": "GAS CERTIFICATION (Gas Safe)",
    "F3": "WATER PRESSURE TESTING CERTIFICATION",
    "F4": "HEATING TESTING CERTIFICATION",
    "F5": "WATER HEATING CERTIFICATION",
    "F6": "DRAINAGE CCTV SURVEY CERTIFICATION",
    "D5": "FENSA OR EQUIVALENT (windows)",
    "E1": "ASBESTOS SURVEY REPORT",
    "_always": [
        "USER MANUALS AND WARRANTIES",
        "BUILDING CONTROL AND APPROVALS"
    ]
}


class SectionC(BaseModel):
    """C — About the Property"""
    property_type: str = ""
    year_built: str = ""
    extensions: str = "None noted"
    conversions: str = "None noted"
    tenure: str = "Assumed freehold"
    storeys: str = ""
    accommodation: str = ""
    construction: str = ""
    council_tax: str = ""
    epc_rating: str = ""
    listed_building: bool = False
    narrative: str = ""


class SectionH(BaseModel):
    """H — Issues for Legal Advisers"""
    narrative: str = ""
    

class SectionI(BaseModel):
    """I — Risks"""
    narrative: str = ""
    asbestos_risk: bool = False
    flood_risk: bool = False
    subsidence_risk: bool = False
    radon_risk: bool = False
    japanese_knotweed: bool = False


class SectionJ(BaseModel):
    """J — Energy Matters"""
    narrative: str = ""
    current_epc: str = ""
    improvements: List[str] = Field(default_factory=list)


class SectionK(BaseModel):
    """K — Surveyor's Declaration"""
    declaration_text: str = (
        'I confirm that I have inspected the property, and I have prepared '
        'this report in line with the RICS Home Survey Standard.'
    )


class SectionL(BaseModel):
    """L — What to do now (Dynamic actions based on property condition)"""
    narrative: str = ""
    urgent_actions: List[str] = Field(default_factory=list)
    pre_purchase_actions: List[str] = Field(default_factory=list)
    ongoing_maintenance: List[str] = Field(default_factory=list)
    professional_referrals: List[str] = Field(default_factory=list)


class SectionM(BaseModel):
    """M — Description of the RICS Home Survey — Level 3"""
    description: str = (
        'The RICS Home Survey – Level 3 (formerly the RICS Building Survey) '
        'is a comprehensive inspection of the property. The surveyor will '
        'carry out a thorough inspection of the property, both inside and '
        'outside, reporting on a wider range of issues than the Level 1 or '
        'Level 2 reports.\n\n'
        'The Level 3 report is suited to all residential properties, and is '
        'particularly appropriate for:\n'
        '- Older properties\n'
        '- Properties that have been altered or extended\n'
        '- Properties where you plan to carry out major renovation or alteration\n'
        '- Unusual properties, or those constructed with uncommon materials\n\n'
    )
    inspection_scope: str = (
        '**What the inspection covers:**\n\n'
        'The surveyor inspects the inside and outside of the main building '
        'and all permanent outbuildings, recording the construction and '
        'defects that are evident. This includes woodwork and other parts of '
        'the structure that are exposed or can be seen. Parts of the '
        'electricity, gas/oil, water, heating and drainage services that can '
        'be seen are inspected. The surveyor does not test the services. '
        'The surveyor notes any damage to the property that may have been '
        'caused by the presence of asbestos.\n\n'
        '**What the inspection does NOT cover:**\n\n'
        'Concealed areas or those obstructed by furniture are not inspected. '
        'The surveyor does not:\'\n'
        '- Move furniture, lift floor coverings or carry out invasive testing\n'
        '- Assess specialist installations (swimming pools, lifts, etc.)\n'
        '- Carry out formal valuations or reinstatement cost assessments\n'
        '- Provide legal/conveyancing advice\n'
    )
    condition_definitions: str = (
        '### Condition rating definitions\n\n'
        '**Condition rating 1 — Green:** No repair is currently needed. '
        'Normal maintenance must be carried out.\n\n'
        '**Condition rating 2 — Amber:** Defects that need repairing or '
        'replacing but are not considered to be either serious or urgent. '
        'The property must be maintained in the normal way.\n\n'
        '**Condition rating 3 — Red:** Defects that are serious and/or '
        'need to be repaired, replaced or investigated urgently.\n\n'
        '**NI — Not inspected:** The element was not inspected and '
        'the reasons are given.\n'
    )
    liability_statement: str = (
        'The report is prepared by a qualified RICS member in accordance '
        'with the RICS Home Survey Standard (effective 1 February 2024). '
        'The surveyor\'s liability for any negligence is limited to the fee '
        'paid for the report unless otherwise agreed in writing. This report '
        'is for the use of the named client only and no liability is '
        'accepted to any third party.\n\n'
        '**Complaints handling:** In the event of any dispute, the '
        'complaints-handling procedure as approved by RICS will be followed. '
        'Details can be obtained from the surveyor\'s office or from RICS '
        'directly.\n\n'
        '© RICS 2024. The RICS Home Survey is reproduced with permission '
        'of the Royal Institution of Chartered Surveyors. Copyright in '
        'all the content of this report belongs to RICS.'
    )


# ============= FULL REPORT =============

class ProjectInfo(BaseModel):
    """Project-level metadata"""
    id: str
    reference: str = ""
    client_name: str = ""
    address: str = ""
    surveyor_name: str = ""
    rics_number: str = ""
    company: str = ""
    qualifications: str = "MRICS"
    inspection_date: str = ""
    report_date: str = ""
    consultation_date: str = ""


class RICSReport(BaseModel):
    """Complete RICS Level 3 Report data model"""
    project: ProjectInfo
    version: str = "v1_draft"
    
    # Sections
    section_a: SectionA = Field(default_factory=SectionA)
    section_b: SectionB = Field(default_factory=SectionB)
    section_c: SectionC = Field(default_factory=SectionC)
    
    # Element sections (dynamic, expand per element)
    section_d_elements: List[RICSElement] = Field(default_factory=list)
    section_e_elements: List[RICSElement] = Field(default_factory=list)
    section_f_elements: List[RICSElement] = Field(default_factory=list)
    section_g_elements: List[RICSElement] = Field(default_factory=list)
    
    # Non-element sections
    section_h: SectionH = Field(default_factory=SectionH)
    section_i: SectionI = Field(default_factory=SectionI)
    section_j: SectionJ = Field(default_factory=SectionJ)
    section_k: SectionK = Field(default_factory=SectionK)
    section_l: SectionL = Field(default_factory=SectionL)
    section_m: SectionM = Field(default_factory=SectionM)
    
    # Photo registry
    all_photos: List[EvidencePhoto] = Field(default_factory=list)
    
    def get_all_elements(self) -> List[RICSElement]:
        """All inspectable elements across D, E, F, G"""
        return (self.section_d_elements + self.section_e_elements +
                self.section_f_elements + self.section_g_elements)
    
    def compute_condition_ratings(self) -> dict:
        """Auto-compute Section B condition rating groups from elements"""
        urgent = []
        attention = []
        ok = []
        not_inspected = []
        
        for elem in self.get_all_elements():
            entry = ConditionRatingEntry(
                code=elem.code, name=elem.name,
                comment=elem.narrative[:100] if elem.narrative else ""
            )
            if elem.condition_rating == ConditionRating.RED:
                urgent.append(entry)
            elif elem.condition_rating == ConditionRating.AMBER:
                attention.append(entry)
            elif elem.condition_rating == ConditionRating.GREEN:
                ok.append(entry)
            else:
                if not entry.comment:
                    entry.comment = "This element was not accessible or not present at the time of inspection."
                not_inspected.append(entry)
        
        return {
            "urgent": urgent,
            "attention": attention,
            "ok": ok,
            "not_inspected": not_inspected
        }
    
    def compute_documents_to_obtain(self) -> List[str]:
        """Auto-compute documents based on which services were inspected"""
        docs = set()
        for elem in self.get_all_elements():
            if elem.code in DOCUMENTS_TO_OBTAIN_MAP:
                docs.add(DOCUMENTS_TO_OBTAIN_MAP[elem.code])
        for d in DOCUMENTS_TO_OBTAIN_MAP["_always"]:
            docs.add(d)
        return sorted(list(docs))
    
    def assign_photo_numbers(self):
        """Assign sequential global numbers to all photos"""
        counter = 1
        for elem in self.get_all_elements():
            for photo in elem.photos:
                photo.global_number = counter
                counter += 1
        self.all_photos = []
        for elem in self.get_all_elements():
            self.all_photos.extend(elem.photos)
