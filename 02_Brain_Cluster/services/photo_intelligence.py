"""
Photo Intelligence Service — Gemini-powered photo analysis for RICS reports.

3-Phase Pipeline:
  Phase 1: Send each context group (audio + photos + timeline) to Gemini
           for per-photo defect analysis and annotation.
  Phase 2: Merge with partial_report.json and classify photos as
           defect/annotated/simple.
  Phase 3: Output enriched photo manifest for template rendering.

Usage:
    service = PhotoIntelligence(project_dir, gemini_service)
    manifest = await service.run()
    # manifest is a dict: element_code -> list of AnnotatedPhoto
"""

import os
import glob
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("photo_intelligence")


@dataclass
class AnnotatedPhoto:
    """A photo enriched with Gemini intelligence."""
    photo_id: str
    path: str
    element_code: str
    context: str
    room_id: str
    room_name: str
    date: str
    # Gemini-generated fields
    what_shows: str = ""
    has_defect: bool = False
    defect_note: str = ""
    condition_flag: str = "NI"
    surveyor_quote: str = ""
    # Display control
    display_mode: str = "simple"  # "evidence_card" | "annotated" | "simple"


class PhotoIntelligence:
    """Gemini-powered photo intelligence for RICS reports."""

    VISION_PROMPT = """You are a RICS Level 3 building surveyor analyzing inspection photos.

For each photo, analyze what is visible and cross-reference with the surveyor's voice recording.

The photos are from the "{context}" inspection of room "{room_name}".

Timeline data (photo timestamps within the audio):
{timeline_json}

Return a JSON array with one object per photo, in the SAME ORDER as the photos provided.
Each object must have these fields:
{{
  "photo_id": "<filename>",
  "what_shows": "<1-line description of what's visible in the photo>",
  "has_defect": true/false,
  "defect_note": "<If defect: professional surveyor description. If no defect: empty string>",
  "condition_flag": "CR1" | "CR2" | "CR3" | "NI",
  "surveyor_said": "<What the surveyor said specifically about this photo, translated to English if needed. Empty if nothing specific>"
}}

Rules:
- CR1 = No significant defects (green)
- CR2 = Defects that need repairing but not urgent (amber)
- CR3 = Serious defects requiring urgent attention (red)
- NI = Not enough info to assess
- Only set has_defect=true if you can SEE a defect in the photo
- surveyor_said should capture the surveyor's exact observation about THIS photo timing
- Keep defect_note under 50 words, professional tone
"""

    def __init__(self, project_dir: str, gemini_service=None):
        self.project_dir = project_dir
        self.gemini = gemini_service
        self._context_groups: List[dict] = []
        self._partial_report: Optional[dict] = None

    async def run(self) -> Dict[str, List[dict]]:
        """Execute the full 3-phase pipeline.
        
        Returns:
            Dict mapping element_code -> list of AnnotatedPhoto dicts
        """
        logger.info(f"Starting Photo Intelligence Pipeline for: {self.project_dir}")

        # Phase 1: Discover context groups and analyze with Gemini
        self._discover_context_groups()
        await self._phase1_vision_analysis()

        # Phase 2: Merge with partial_report and classify
        self._load_partial_report()
        self._phase2_smart_assembly()

        # Phase 3: Build element-grouped manifest
        manifest = self._phase3_build_manifest()

        total = sum(len(photos) for photos in manifest.values())
        defects = sum(
            1 for photos in manifest.values()
            for p in photos if p.get("has_defect")
        )
        logger.info(
            f"Photo Intelligence complete: {total} photos, "
            f"{defects} defects, {len(manifest)} elements"
        )

        return manifest

    # ─────────────────── DISCOVERY ───────────────────

    def _discover_context_groups(self):
        """Discover all context groups (audio + photos + timeline) per context folder."""
        self._context_groups = []

        for session_dir in glob.glob(os.path.join(self.project_dir, "*_Session_*")):
            if not os.path.isdir(session_dir):
                continue

            session_date = os.path.basename(session_dir)[:10]

            for room_dir in sorted(os.listdir(session_dir)):
                room_path = os.path.join(session_dir, room_dir)
                if not os.path.isdir(room_path):
                    continue

                room_name = self._get_room_name(room_path)

                for context_dir in sorted(os.listdir(room_path)):
                    context_path = os.path.join(room_path, context_dir)
                    if not os.path.isdir(context_path) or not context_dir.startswith("Context_"):
                        continue

                    context_name = context_dir.replace("Context_", "")

                    # Gather photos
                    photos = sorted(glob.glob(os.path.join(context_path, "img_*.jpg")))
                    if not photos:
                        continue

                    # Find audio
                    audio_files = glob.glob(os.path.join(context_path, "audio_*.m4a"))
                    audio_path = audio_files[0] if audio_files else None

                    # Find timeline
                    timeline_files = glob.glob(os.path.join(context_path, "timeline_*.json"))
                    timeline_data = None
                    if timeline_files:
                        try:
                            with open(timeline_files[0]) as f:
                                timeline_data = json.load(f)
                        except Exception:
                            pass

                    group = {
                        "context": context_name,
                        "room_id": room_dir,
                        "room_name": room_name,
                        "session_date": session_date,
                        "photos": photos,
                        "audio_path": audio_path,
                        "timeline": timeline_data,
                        "annotations": [],  # Filled by Phase 1
                    }
                    self._context_groups.append(group)

                    logger.info(
                        f"Context group: {context_name} in {room_name} — "
                        f"{len(photos)} photos, audio={'yes' if audio_path else 'no'}"
                    )

        logger.info(f"Discovered {len(self._context_groups)} context groups")

    # ─────────────────── PHASE 1: VISION ───────────────────

    async def _phase1_vision_analysis(self):
        """Send each context group to Gemini for per-photo analysis."""
        if not self.gemini:
            logger.warning("No Gemini service — using fallback annotations")
            self._phase1_fallback()
            return

        for group in self._context_groups:
            try:
                annotations = await self._analyze_context_group(group)
                group["annotations"] = annotations
                logger.info(
                    f"Phase 1: {group['context']} — "
                    f"{len(annotations)} annotations, "
                    f"{sum(1 for a in annotations if a.get('has_defect'))} defects"
                )
            except Exception as e:
                logger.error(f"Phase 1 failed for {group['context']}: {e}")
                group["annotations"] = self._build_fallback_annotations(group)

    async def _analyze_context_group(self, group: dict) -> List[dict]:
        """Single Gemini multimodal call for one context group."""
        timeline_str = json.dumps(group.get("timeline", {}), indent=2, default=str)

        prompt = self.VISION_PROMPT.format(
            context=group["context"].replace("_", " "),
            room_name=group["room_name"],
            timeline_json=timeline_str,
        )

        # Call Gemini with photos + audio
        response_text = await self.gemini.analyze_evidence(
            images_paths=group["photos"],
            audio_path=group.get("audio_path"),
            prompt_text=prompt,
        )

        # Parse JSON response
        try:
            annotations = json.loads(response_text)
            if isinstance(annotations, dict) and "error" in annotations:
                logger.error(f"Gemini error: {annotations}")
                return self._build_fallback_annotations(group)
            if not isinstance(annotations, list):
                annotations = [annotations]
            return annotations
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Gemini response: {response_text[:200]}")
            return self._build_fallback_annotations(group)

    def _phase1_fallback(self):
        """Fallback: create basic annotations without Gemini."""
        for group in self._context_groups:
            group["annotations"] = self._build_fallback_annotations(group)

    def _build_fallback_annotations(self, group: dict) -> List[dict]:
        """Build basic annotations from file names and context."""
        annotations = []
        for photo_path in group["photos"]:
            annotations.append({
                "photo_id": os.path.basename(photo_path),
                "what_shows": f"{group['context'].replace('_', ' ')} — {group['room_name']}",
                "has_defect": False,
                "defect_note": "",
                "condition_flag": "NI",
                "surveyor_said": "",
            })
        return annotations

    # ─────────────────── PHASE 2: ASSEMBLY ───────────────────

    def _load_partial_report(self):
        """Load partial_report.json for defect data."""
        for session_dir in glob.glob(os.path.join(self.project_dir, "*_Session_*")):
            for room_dir in os.listdir(session_dir):
                report_path = os.path.join(session_dir, room_dir, "partial_report.json")
                if os.path.exists(report_path):
                    try:
                        with open(report_path) as f:
                            self._partial_report = json.load(f)
                        logger.info(f"Loaded partial_report from: {report_path}")
                        return
                    except Exception as e:
                        logger.error(f"Failed to load partial_report: {e}")

    def _phase2_smart_assembly(self):
        """Merge Gemini annotations with partial_report defect data."""
        if not self._partial_report:
            logger.warning("No partial_report.json — using Gemini annotations only")
            return

        # Build a lookup: photo_filename -> element defects from partial_report
        photo_defects = {}
        for element in self._partial_report.get("elements", []):
            defects = element.get("defects_identified", [])
            for photo_path in element.get("evidence_photos", []):
                photo_id = os.path.basename(photo_path)
                if defects:
                    photo_defects[photo_id] = {
                        "element": element.get("rics_element", ""),
                        "condition_rating": element.get("condition_rating", 0),
                        "defects": defects,
                        "description": element.get("condition_description", ""),
                    }

        # Enrich annotations with partial_report defect data
        for group in self._context_groups:
            for ann in group["annotations"]:
                photo_id = ann.get("photo_id", "")
                if photo_id in photo_defects:
                    pr_data = photo_defects[photo_id]

                    # If Gemini didn't find a defect but partial_report has one, merge
                    if not ann["has_defect"] and pr_data["defects"]:
                        defect = pr_data["defects"][0]
                        if defect.get("severity", "").lower() in ("moderate", "significant", "severe"):
                            ann["has_defect"] = True
                            ann["defect_note"] = (
                                f"{defect.get('defect_type', 'Defect')} — "
                                f"{defect.get('recommended_action', 'Further investigation required')}"
                            )

                    # Map condition rating
                    cr = pr_data.get("condition_rating", 0)
                    if cr == 3:
                        ann["condition_flag"] = "CR3"
                    elif cr == 2:
                        ann["condition_flag"] = "CR2"
                    elif cr == 1:
                        ann["condition_flag"] = "CR1"

        logger.info(f"Phase 2: Merged {len(photo_defects)} photo-defect links from partial_report")

    # ─────────────────── PHASE 3: MANIFEST ───────────────────

    def _phase3_build_manifest(self) -> Dict[str, List[dict]]:
        """Build element-grouped manifest of annotated photos."""
        from services.photo_discovery import CONTEXT_TO_ELEMENT

        manifest: Dict[str, List[dict]] = {}

        for group in self._context_groups:
            context = group["context"]
            element_code = CONTEXT_TO_ELEMENT.get(context, "GEN")

            for i, photo_path in enumerate(group["photos"]):
                photo_id = os.path.basename(photo_path)

                # Get Gemini annotation for this photo
                ann = {}
                if i < len(group["annotations"]):
                    ann = group["annotations"][i]

                has_defect = ann.get("has_defect", False)
                surveyor_said = ann.get("surveyor_said", "")

                # Determine display mode
                if has_defect:
                    display_mode = "evidence_card"
                elif surveyor_said:
                    display_mode = "annotated"
                else:
                    display_mode = "simple"

                photo = AnnotatedPhoto(
                    photo_id=photo_id,
                    path=photo_path,
                    element_code=element_code,
                    context=context,
                    room_id=group["room_id"],
                    room_name=group["room_name"],
                    date=group["session_date"],
                    what_shows=ann.get("what_shows", f"{context.replace('_', ' ')} — {group['room_name']}"),
                    has_defect=has_defect,
                    defect_note=ann.get("defect_note", ""),
                    condition_flag=ann.get("condition_flag", "NI"),
                    surveyor_quote=surveyor_said,
                    display_mode=display_mode,
                )

                if element_code not in manifest:
                    manifest[element_code] = []
                manifest[element_code].append(asdict(photo))

        return manifest

    # ─────────────────── HELPERS ───────────────────

    @staticmethod
    def _get_room_name(room_path: str) -> str:
        """Extract room name from partial_report.json."""
        report_path = os.path.join(room_path, "partial_report.json")
        if os.path.exists(report_path):
            try:
                with open(report_path) as f:
                    return json.load(f).get("room_name", os.path.basename(room_path))
            except Exception:
                pass
        return os.path.basename(room_path)
