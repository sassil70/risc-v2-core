"""
Voice Report Editor — AI-powered voice editing of RICS reports.
Parses voice commands and applies edits to the Markdown report.
"""

import json
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger("voice_report_editor")

# Section code aliases for voice recognition
SECTION_ALIASES = {
    "a": "A", "about": "A", "inspection": "A",
    "b": "B", "opinion": "B", "overall": "B", "summary": "B", "condition": "B",
    "c": "C", "property": "C", "about property": "C",
    "d": "D", "outside": "D", "external": "D", "exterior": "D",
    "e": "E", "inside": "E", "internal": "E", "interior": "E",
    "f": "F", "services": "F", "utilities": "F",
    "g": "G", "grounds": "G", "garden": "G",
    "h": "H", "legal": "H",
    "i": "I", "risks": "I", "risk": "I",
    "j": "J", "energy": "J",
}

ELEMENT_ALIASES = {
    "chimney": "D1", "chimneys": "D1", "stack": "D1", "stacks": "D1",
    "roof coverings": "D2", "roof tiles": "D2", "tiles": "D2",
    "gutters": "D3", "rainwater": "D3", "downpipes": "D3",
    "walls": "D4", "main walls": "D4", "brickwork": "D4",
    "windows": "D5", "glazing": "D5",
    "doors": "D6", "outside doors": "D6",
    "conservatory": "D7", "porch": "D7",
    "roof structure": "E1", "loft": "E1", "attic": "E1",
    "ceilings": "E2", "ceiling": "E2",
    "partitions": "E3", "internal walls": "E3",
    "floors": "E4", "flooring": "E4",
    "fireplaces": "E5", "fireplace": "E5", "flues": "E5",
    "fittings": "E6", "kitchen fittings": "E6",
    "woodwork": "E7", "staircase": "E7", "stairs": "E7",
    "bathroom": "E8", "bath": "E8", "shower": "E8",
    "electricity": "F1", "electrics": "F1", "wiring": "F1",
    "gas": "F2", "oil": "F2",
    "water": "F3", "plumbing": "F3",
    "heating": "F4", "boiler": "F4", "radiators": "F4",
    "hot water": "F5", "water heating": "F5",
    "drainage": "F6", "drains": "F6",
    "garage": "G1",
    "outbuildings": "G2", "shed": "G2",
    "boundaries": "G3", "fencing": "G3", "driveway": "G3",
    "trees": "G4", "tree": "G4",
}

# Action verbs
ADD_VERBS = {"add", "insert", "append", "include", "note", "mention", "record"}
EDIT_VERBS = {"edit", "change", "modify", "update", "correct", "fix", "rewrite", "replace"}
DELETE_VERBS = {"delete", "remove", "drop", "clear"}
RATING_VERBS = {"rate", "rating", "set rating", "change rating", "condition"}


class VoiceReportEditor:
    """Processes voice commands to edit RICS Markdown reports."""
    
    def __init__(self, gemini_service=None):
        self.gemini_service = gemini_service
    
    def parse_command(self, voice_text: str) -> dict:
        """
        Parse a voice command into structured intent.
        
        Returns:
            {
                "action": "add_note"|"edit_section"|"change_rating"|"rewrite"|"delete_note",
                "section": "D"|"E"|...,
                "element": "D1"|"E2"|...,
                "content": "the additional text...",
                "rating": 1|2|3 (if applicable),
                "confidence": 0.0-1.0
            }
        """
        text = voice_text.strip().lower()
        result = {
            "action": "add_note",
            "section": None,
            "element": None,
            "content": voice_text,
            "rating": None,
            "confidence": 0.5
        }
        
        # 1. Detect element
        for alias, code in sorted(ELEMENT_ALIASES.items(), key=lambda x: -len(x[0])):
            if alias in text:
                result["element"] = code
                result["section"] = code[0]
                result["confidence"] = 0.8
                break
        
        # 2. If no element, detect section
        if not result["element"]:
            for alias, code in sorted(SECTION_ALIASES.items(), key=lambda x: -len(x[0])):
                if alias in text:
                    result["section"] = code
                    result["confidence"] = 0.6
                    break
        
        # 3. Detect element from code pattern (e.g. "D2", "E1")
        code_match = re.search(r'\b([DEFG]\d)\b', voice_text, re.IGNORECASE)
        if code_match:
            result["element"] = code_match.group(1).upper()
            result["section"] = result["element"][0]
            result["confidence"] = 0.9
        
        # 4. Detect action
        words = set(text.split())
        if words & ADD_VERBS:
            result["action"] = "add_note"
        elif words & EDIT_VERBS:
            result["action"] = "edit_section"
        elif words & DELETE_VERBS:
            result["action"] = "delete_note"
        elif words & RATING_VERBS:
            result["action"] = "change_rating"
            # Extract rating number
            rating_match = re.search(r'rating\s*(\d)', text)
            if rating_match:
                result["rating"] = int(rating_match.group(1))
        
        # 5. Extract content (everything after the element/section identifier)
        if result["element"]:
            # Remove the element reference from content
            element_pattern = re.compile(
                re.escape(result["element"]) + r'[:\s]*', re.IGNORECASE
            )
            result["content"] = element_pattern.sub('', voice_text).strip()
            # Also remove action verbs
            for verb in ADD_VERBS | EDIT_VERBS | DELETE_VERBS | RATING_VERBS:
                result["content"] = re.sub(
                    r'\b' + re.escape(verb) + r'\b', '', result["content"], flags=re.IGNORECASE
                ).strip()
        
        return result
    
    async def apply_edit(
        self, 
        md_content: str, 
        voice_text: str,
        use_gemini: bool = True
    ) -> Tuple[str, dict]:
        """
        Apply a voice edit to the Markdown report.
        
        Returns:
            (updated_md, edit_info)
        """
        command = self.parse_command(voice_text)
        
        if use_gemini and self.gemini_service:
            return await self._apply_with_gemini(md_content, command, voice_text)
        else:
            return self._apply_simple(md_content, command)
    
    async def _apply_with_gemini(
        self, md_content: str, command: dict, voice_text: str
    ) -> Tuple[str, dict]:
        """Use Gemini to intelligently apply the edit"""
        prompt = f"""You are a RICS report editor AI. A surveyor gave this voice command:

VOICE COMMAND: "{voice_text}"

PARSED INTENT:
- Action: {command['action']}
- Section: {command['section']}
- Element: {command['element']}
- Content: {command['content']}
- Rating change: {command['rating']}

CURRENT REPORT (Markdown):
```markdown
{md_content[:5000]}
```

Apply the voice command to the report. Only modify the relevant section/element.
Return the COMPLETE updated Markdown report.

If the command is unclear, make your best professional judgment as an expert RICS surveyor.
If changing a condition rating, also update the narrative to reflect the new assessment.

Return ONLY the updated Markdown, no explanation."""

        try:
            response = self.gemini_service.model.generate_content(prompt)
            updated_md = response.text
            # Clean up any code fences
            updated_md = updated_md.strip()
            if updated_md.startswith("```"):
                updated_md = updated_md.split("```", 2)[1]
                if updated_md.startswith("markdown"):
                    updated_md = updated_md[8:]
            if updated_md.endswith("```"):
                updated_md = updated_md[:-3]
            
            command["applied"] = True
            command["method"] = "gemini"
            return updated_md.strip(), command
        except Exception as e:
            logger.error(f"Gemini edit failed: {e}")
            return self._apply_simple(md_content, command)
    
    def _apply_simple(
        self, md_content: str, command: dict
    ) -> Tuple[str, dict]:
        """Simple text-based edit (fallback without Gemini)"""
        if command["action"] == "add_note" and command["element"]:
            # Find the element section and add note
            marker = f'{command["element"]} '  # e.g. "D2 "
            if marker in md_content:
                # Find the end of the element's narrative
                parts = md_content.split(marker, 1)
                if len(parts) == 2:
                    # Add note after the first paragraph
                    insert_text = f"\n\n**Additional note**: {command['content']}\n"
                    
                    # Find next element or section break
                    next_break = parts[1].find("\n---\n")
                    if next_break > 0:
                        updated = (
                            parts[0] + marker + 
                            parts[1][:next_break] + insert_text + 
                            parts[1][next_break:]
                        )
                        command["applied"] = True
                        command["method"] = "simple_insert"
                        return updated, command
        
        command["applied"] = False
        command["method"] = "none"
        command["error"] = "Could not apply edit without Gemini"
        return md_content, command
    
    def generate_diff(self, old_md: str, new_md: str) -> str:
        """Generate a human-readable diff between two Markdown versions"""
        old_lines = old_md.splitlines()
        new_lines = new_md.splitlines()
        
        diff_lines = []
        import difflib
        for line in difflib.unified_diff(old_lines, new_lines, lineterm='', n=2):
            diff_lines.append(line)
        
        return "\n".join(diff_lines)
