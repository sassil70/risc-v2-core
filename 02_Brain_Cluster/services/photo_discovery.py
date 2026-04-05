"""
Photo Discovery Service — Scans project directories for inspection photos
and builds structured photo lists for RICS report generation.

Photos are stored in:
  /app/storage/Projects/{project_slug}/
    {session_id}/
      {room_id}/
        Context_{element_name}/
          img_*.jpg
          audio_*.m4a
          timeline_*.json

This service:
1. Finds all session/room directories
2. Discovers photos in Context_* subdirectories
3. Maps Context names to RICS element codes
4. Returns photo lists with absolute paths and metadata
"""

import os
import glob
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("photo_discovery")

# Map Context folder names to RICS element keywords
CONTEXT_TO_ELEMENT = {
    # Section D — Outside the property
    "Chimney": "D1",           # D1 Chimney stacks
    "Roof": "D2",              # D2 Roof coverings
    "Gutters": "D3",           # D3 Rainwater pipes and gutters
    "External_Walls": "D4",    # D4 Main walls
    "Windows": "D5",           # D5 Windows
    "Doors": "D6",             # D6 Outside doors (incl patio)
    "Conservatory": "D7",      # D7 Conservatory and porches
    # Section E — Inside the property
    "Ceiling": "E2",           # E2 Ceilings (NOT E1 = Roof structure)
    "Walls": "E3",             # E3 Walls and partitions
    "Floor": "E4",             # E4 Floors
    "Fireplace": "E5",         # E5 Fireplaces, chimney breasts
    "Kitchen": "E6",           # E6 Built-in fittings
    "Staircase": "E7",         # E7 Woodwork / staircase joinery
    "Bathroom": "E8",          # E8 Bathroom fittings
    # Section F — Services
    "Electricity": "F1",       # F1 Electricity
    "Gas": "F2",               # F2 Gas/oil
    "Water": "F3",             # F3 Water
    "Heating": "F4",           # F4 Heating
    "Water_Heating": "F5",     # F5 Water heating
    "Plumbing": "F3",          # F3 Water (alias)
    "Drainage": "F6",          # F6 Drainage
    # Section G — Grounds
    "Garage": "G1",            # G1 Garage
    "Outbuilding": "G2",       # G2 Permanent outbuildings
    "Garden": "G3",            # G3 Outside areas and boundaries
    "Trees": "G4",             # G4 Trees
    # Wildcard
    "General_Context": "GEN",  # General photos — distributed across active elements
}


def discover_project_photos(project_dir: str) -> Dict[str, List[dict]]:
    """
    Scan a project directory and discover all inspection photos.
    
    Returns:
        Dict mapping room_id → list of photo dicts with:
        {
            "id": "img_123456.jpg",
            "path": "/absolute/path/to/img_123456.jpg",
            "caption": "Ceiling inspection photo",
            "date": "2026-03-20",
            "context": "Ceiling",
            "element_code": "E1",
            "room_id": "general_ab029c2a",
            "room_name": "Room Name"
        }
    """
    rooms_photos: Dict[str, List[dict]] = {}
    
    if not os.path.exists(project_dir):
        logger.warning(f"Project directory not found: {project_dir}")
        return rooms_photos
    
    # Find all session directories (format: YYYY-MM-DD_Session_*)
    for session_dir in glob.glob(os.path.join(project_dir, "*_Session_*")):
        if not os.path.isdir(session_dir):
            continue
        
        session_date = os.path.basename(session_dir)[:10]  # "2026-03-20"
        
        # Find all room directories within session
        for room_dir in sorted(os.listdir(session_dir)):
            room_path = os.path.join(session_dir, room_dir)
            if not os.path.isdir(room_path):
                continue
            
            room_id = room_dir
            room_name = _get_room_name(room_path)
            photos = []
            
            # Scan Context_* subdirectories
            for context_dir in sorted(os.listdir(room_path)):
                context_path = os.path.join(room_path, context_dir)
                if not os.path.isdir(context_path) or not context_dir.startswith("Context_"):
                    continue
                
                context_name = context_dir.replace("Context_", "")
                element_code = CONTEXT_TO_ELEMENT.get(context_name, "")
                
                # Find all image files
                for img_file in sorted(glob.glob(os.path.join(context_path, "img_*.jpg"))):
                    photo = {
                        "id": os.path.basename(img_file),
                        "path": img_file,  # Absolute path
                        "caption": f"{context_name.replace('_', ' ')} — {room_name}",
                        "date": session_date,
                        "context": context_name,
                        "element_code": element_code,
                        "room_id": room_id,
                        "room_name": room_name,
                    }
                    photos.append(photo)
            
            if photos:
                rooms_photos[room_id] = photos
                logger.info(f"Discovered {len(photos)} photos for room '{room_name}' ({room_id})")
    
    total = sum(len(p) for p in rooms_photos.values())
    logger.info(f"Total photos discovered: {total} across {len(rooms_photos)} rooms")
    
    return rooms_photos


def enrich_rooms_with_photos(
    rooms_data: List[dict],
    project_dir: str
) -> List[dict]:
    """
    Enrich room data with discovered photos.
    This bridges the gap between DB room metadata and filesystem photos.
    
    Args:
        rooms_data: Room list from DB (may have empty/missing 'photos' key)
        project_dir: Absolute path to project directory
    
    Returns:
        Same rooms_data but with 'photos' lists populated
    """
    discovered = discover_project_photos(project_dir)
    
    if not discovered:
        logger.warning("No photos discovered — rooms will have empty photo lists")
        return rooms_data
    
    # If rooms_data is empty but we have photos, create room entries from discovery
    if not rooms_data:
        logger.info("No room data from DB, building from filesystem discovery")
        for room_id, photos in discovered.items():
            room_name = photos[0]["room_name"] if photos else room_id
            
            # Build notes from timeline JSONs if available
            notes = _extract_notes_from_timelines(
                os.path.dirname(photos[0]["path"]) if photos else ""
            )
            
            rooms_data.append({
                "id": room_id,
                "name": room_name,
                "type": _infer_room_type(room_name),
                "notes": notes,
                "photos": photos,
            })
        return rooms_data
    
    # Match discovered photos to existing rooms
    for room in rooms_data:
        room_id = room.get("id", "")
        room_name = room.get("name", "")
        
        # Try to match by room_id
        matched_photos = discovered.get(room_id, [])
        
        # If no match by ID, try fuzzy match by name
        if not matched_photos:
            for disc_id, disc_photos in discovered.items():
                if disc_photos and room_name.lower() in disc_photos[0].get("room_name", "").lower():
                    matched_photos = disc_photos
                    break
        
        # If still no match, distribute all discovered photos (single-room projects)
        if not matched_photos and len(discovered) == 1:
            matched_photos = list(discovered.values())[0]
        
        if matched_photos:
            existing = room.get("photos", [])
            room["photos"] = existing + matched_photos
            logger.info(f"Enriched room '{room_name}' with {len(matched_photos)} photos")
    
    return rooms_data


def _get_room_name(room_path: str) -> str:
    """Extract room name from partial_report.json if available."""
    report_path = os.path.join(room_path, "partial_report.json")
    if os.path.exists(report_path):
        try:
            with open(report_path) as f:
                data = json.load(f)
            return data.get("room_name", os.path.basename(room_path))
        except Exception:
            pass
    return os.path.basename(room_path)


def _infer_room_type(room_name: str) -> str:
    """Infer room type from room name for RICS element mapping."""
    name_lower = room_name.lower()
    
    type_keywords = {
        "kitchen": "kitchen",
        "bathroom": "bathroom",
        "bedroom": "bedroom",
        "living": "living_room",
        "reception": "reception",
        "dining": "dining_room",
        "hallway": "hallway",
        "landing": "landing",
        "attic": "attic",
        "loft": "loft",
        "garage": "garage",
        "garden": "garden",
        "utility": "utility",
        "toilet": "toilet",
        "conservatory": "conservatory",
        "porch": "porch",
        "office": "living_room",
        "general": "general",
    }
    
    for keyword, room_type in type_keywords.items():
        if keyword in name_lower:
            return room_type
    
    return "general"


def _extract_notes_from_timelines(room_path: str) -> List[str]:
    """Extract observation notes from timeline JSON files."""
    notes = []
    parent_dir = os.path.dirname(room_path) if not os.path.isdir(room_path) else room_path
    
    for timeline_file in glob.glob(os.path.join(parent_dir, "**", "timeline_*.json"), recursive=True):
        try:
            with open(timeline_file) as f:
                timeline = json.load(f)
            
            # Extract text entries from timeline
            if isinstance(timeline, list):
                for entry in timeline:
                    if isinstance(entry, dict):
                        text = entry.get("transcription", "") or entry.get("text", "") or entry.get("note", "")
                        if text:
                            notes.append(text)
            elif isinstance(timeline, dict):
                text = timeline.get("transcription", "") or timeline.get("text", "")
                if text:
                    notes.append(text)
        except Exception:
            continue
    
    return notes
