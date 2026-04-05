"""
Room → RICS Element Mapper
Maps room inspection data to standard RICS elements (D1-G5).
Each room contains observations that map to multiple RICS elements.
"""

from typing import Dict, List, Optional
from services.rics_schema import RICSElement, ConditionRating, EvidencePhoto, ALL_RICS_ELEMENTS


# Room type → which RICS elements it contributes to
ROOM_ELEMENT_MAPPING = {
    # EVERY room contributes to these interior elements
    "_all_rooms": ["E2", "E3", "E4", "E7"],
    
    # Specific room types contribute to specific elements
    "attic": ["E1"],                            # Roof structure
    "loft": ["E1"],
    "living_room": ["E5", "E6"],                # Fireplaces, built-in fittings
    "reception": ["E5", "E6"],
    "dining_room": ["E5", "E6"],
    "kitchen": ["E6", "E8", "F3", "F4", "F5"], # Fittings, water, heating
    "bathroom": ["E8", "F3", "F5"],             # Bathroom fittings, water
    "wet_room": ["E8", "F3", "F5"],
    "toilet": ["E8", "F3"],
    "utility": ["E6", "F1", "F2", "F3"],        # Electrics, gas, water
    "bedroom": ["E6"],
    "hallway": ["E7"],                          # Staircase joinery
    "landing": ["E7"],
    "garage": ["G1"],
    "garden": ["G3", "G4"],
    "outbuilding": ["G2"],
    "conservatory": ["D7"],
    "porch": ["D7"],
    "external_front": ["D1", "D2", "D3", "D4", "D5", "D6", "D8"],
    "external_rear": ["D1", "D2", "D3", "D4", "D5", "D6", "D8"],
    "external_side": ["D4", "D5", "D8"],
    "roof": ["D1", "D2", "D3"],
}

# Keywords in observation notes that suggest specific elements
KEYWORD_ELEMENT_MAP = {
    # Structural/External
    "chimney": "D1", "stack": "D1", "pot": "D1", "cowl": "D1", "flue": "E5",
    "roof": "D2", "tile": "D2", "slate": "D2", "ridge": "D2", "hip": "D2",
    "gutter": "D3", "downpipe": "D3", "rainwater": "D3", "hopper": "D3",
    "wall": "D4", "brick": "D4", "render": "D4", "pointing": "D4", "crack": "D4",
    "window": "D5", "glazing": "D5", "double glaz": "D5", "sash": "D5",
    "door": "D6", "patio": "D6",
    "conservatory": "D7", "porch": "D7",
    
    # Interior
    "ceiling": "E2", "lath": "E2", "plaster": "E2",
    "partition": "E3", "damp": "E3", "moisture": "E3",
    "floor": "E4", "board": "E4", "carpet": "E4", "laminate": "E4",
    "fireplace": "E5", "chimney breast": "E5",
    "kitchen": "E6", "cupboard": "E6", "worktop": "E6", "built-in": "E6",
    "stair": "E7", "banister": "E7", "handrail": "E7", "newel": "E7",
    "bath": "E8", "shower": "E8", "basin": "E8", "toilet": "E8", "wc": "E8",
    
    # Services
    "electric": "F1", "wire": "F1", "consumer": "F1", "socket": "F1", "rcd": "F1",
    "gas": "F2", "meter": "F2", "boiler": "F4", "central heat": "F4",
    "water": "F3", "pipe": "F3", "plumb": "F3", "stopcock": "F3",
    "radiator": "F4", "heating": "F4", "thermostat": "F4",
    "hot water": "F5", "cylinder": "F5", "immersion": "F5",
    "drain": "F6", "manhole": "F6", "sewer": "F6",
    
    # Grounds
    "garage": "G1", 
    "shed": "G2", "outbuilding": "G2",
    "garden": "G3", "path": "G3", "fence": "G3", "boundary": "G3", "driveway": "G3",
    "tree": "G4",
}


def map_room_to_elements(
    room_id: str,
    room_type: str,
    notes: List[str],
    photos: List[dict],
    damp_readings: Optional[Dict[str, float]] = None
) -> Dict[str, dict]:
    """
    Map a single room's inspection data to RICS elements.
    
    Returns dict of element_code → {notes, photos, damp_readings}
    """
    result: Dict[str, dict] = {}
    
    # 1. Get base elements from room type
    base_elements = set(ROOM_ELEMENT_MAPPING.get("_all_rooms", []))
    room_type_lower = room_type.lower().replace(" ", "_")
    
    for rt_key, rt_elements in ROOM_ELEMENT_MAPPING.items():
        if rt_key == "_all_rooms":
            continue
        if rt_key in room_type_lower:
            base_elements.update(rt_elements)
    
    # Initialize all base elements
    for elem_code in base_elements:
        if elem_code not in result:
            result[elem_code] = {"notes": [], "photos": [], "damp_readings": {}}
    
    # 2. Map notes by keyword analysis
    for note in notes:
        note_lower = note.lower()
        matched_elements = set()
        
        for keyword, elem_code in KEYWORD_ELEMENT_MAP.items():
            if keyword in note_lower:
                matched_elements.add(elem_code)
        
        # Add note to matched elements
        for elem_code in matched_elements:
            if elem_code not in result:
                result[elem_code] = {"notes": [], "photos": [], "damp_readings": {}}
            result[elem_code]["notes"].append(note)
        
        # If no keyword match, add to all base elements
        if not matched_elements:
            for elem_code in base_elements:
                result[elem_code]["notes"].append(note)
    
    # 3. Map photos — prefer direct element_code from Context discovery,
    #    fallback to keyword matching, then to base elements
    for photo in photos:
        # Direct mapping: photo already has element_code from Context_* discovery
        direct_code = photo.get("element_code", "")
        if direct_code and direct_code != "GEN":
            if direct_code not in result:
                result[direct_code] = {"notes": [], "photos": [], "damp_readings": {}}
            result[direct_code]["photos"].append(photo)
            continue
        
        # Keyword matching from caption
        photo_caption = (photo.get("caption", "") or "").lower()
        photo_mapped = False
        
        for keyword, elem_code in KEYWORD_ELEMENT_MAP.items():
            if keyword in photo_caption:
                if elem_code not in result:
                    result[elem_code] = {"notes": [], "photos": [], "damp_readings": {}}
                result[elem_code]["photos"].append(photo)
                photo_mapped = True
                break
        
        if not photo_mapped:
            # Distribute GEN / unmatched photos across base elements
            for elem_code in sorted(base_elements):
                result[elem_code]["photos"].append(photo)
                break
    
    # 4. Map damp readings
    if damp_readings:
        for loc, reading in damp_readings.items():
            # Damp readings always map to E3 (Walls) and potentially F3 (Water)
            for ec in ["E3"]:
                if ec not in result:
                    result[ec] = {"notes": [], "photos": [], "damp_readings": {}}
                result[ec]["damp_readings"][f"{room_id}:{loc}"] = reading
    
    return result


def aggregate_room_data_to_elements(
    rooms: List[dict]
) -> Dict[str, RICSElement]:
    """
    Aggregate data from ALL rooms into unified RICS elements.
    
    Args:
        rooms: List of room dicts with keys: id, name, type, notes[], photos[], damp_readings{}
    
    Returns:
        Dict of element_code → RICSElement (ready for Gemini narrative generation)
    """
    # Initialize all standard elements
    elements: Dict[str, RICSElement] = {}
    for elem_def in ALL_RICS_ELEMENTS:
        elements[elem_def["code"]] = RICSElement(**elem_def)
    
    # Map each room's data to elements
    for room in rooms:
        room_id = room.get("id", "unknown")
        room_type = room.get("type", "general")
        room_name = room.get("name", room_type)
        notes = room.get("notes", [])
        photos = room.get("photos", [])
        damp = room.get("damp_readings", {})
        
        mapped = map_room_to_elements(room_id, room_type, notes, photos, damp)
        
        for elem_code, data in mapped.items():
            if elem_code in elements:
                elem = elements[elem_code]
                elem.source_rooms.append(room_name)
                elem.raw_notes.extend(data["notes"])
                
                for p in data["photos"]:
                    elem.photos.append(EvidencePhoto(
                        photo_id=p.get("id", ""),
                        path=p.get("path", ""),
                        caption=p.get("caption", ""),
                        date=p.get("date", ""),
                        room_id=room_id,
                        element_code=elem_code,
                        section_code=elem_code[0]
                    ))
                
                if data.get("damp_readings"):
                    if elem.damp_readings is None:
                        elem.damp_readings = {}
                    elem.damp_readings.update(data["damp_readings"])
    
    # Remove duplicates in source_rooms
    for elem in elements.values():
        elem.source_rooms = list(set(elem.source_rooms))
    
    return elements
