import re
import os
import logging
from typing import Dict, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KnowledgeLoader")

class KnowledgeLoader:
    _instance = None
    _knowledge_cache: Dict[str, str] = {}
    
    # Path to the source of truth (The Knowledge Cache)
    # Adjust this path if deployed in Docker to the correct mount point
    KNOWLEDGE_PATH = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\Smart_Surveyor_NextGen\01_Control_Module\control_backend\knowledge_cache.txt"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KnowledgeLoader, cls).__new__(cls)
            cls._instance.load_knowledge()
        return cls._instance

    def load_knowledge(self) -> None:
        """
        Loads the raw text file and parses it into semantic chunks.
        """
        if not os.path.exists(self.KNOWLEDGE_PATH):
            logger.error(f"Knowledge file not found at {self.KNOWLEDGE_PATH}")
            return

        try:
            with open(self.KNOWLEDGE_PATH, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            
            logger.info(f"Loaded {len(raw_text)} bytes of knowledge.")
            self._parse_sections(raw_text)
            
        except Exception as e:
            logger.error(f"Failed to load knowledge: {e}")

    def _parse_sections(self, text: str) -> None:
        """
        Splits the text into logical sections (e.g., E3 Walls, E4 Floors).
        Uses simple header detection for now.
        """
        # Generic sections to find
        sections_map = {
            "D4 Main walls": ["D4", "Main walls"],
            "E3 Walls and partitions": ["E3", "Walls and partitions"],
            "E4 Floors": ["E4", "Floors"],
            "E2 Ceilings": ["E2", "Ceilings"],
            "E5 Fireplaces": ["E5", "Fireplaces"],
            "E6 Built-in fittings": ["E6", "Built-in kitchen"],
            "F1 Electricity": ["F1", "Electricity"],
            "F2 Gas": ["F2", "Gas"],
            "F3 Water": ["F3", "Water"],
            "Condition ratings": ["Condition ratings"]
        }
        
        # Default fallback
        self._knowledge_cache["General"] = text[:2000] # First 2000 chars as general context
        
        # Basic chunking loop (This can be improved with regex specific to PDF layout)
        # For V1, we simply store the whole text as "Full_Context" and specific keywords map to it.
        # Ideally, we would split by "E3 Walls" and take text until next header.
        
        # Improved Regex Splitting Strategy
        # Look for patterns like "E3 Walls" at start of lines
        
        lines = text.split('\n')
        current_section = "General"
        buffer = []
        
        # Regex to match headers like "E3 Walls", "D4 Main walls", "Section B"
        header_pattern = re.compile(r'^([A-Z][0-9]+)\s+(.+)$')
        
        for line in lines:
            line = line.strip()
            match = header_pattern.match(line)
            
            if match:
                # Save previous section
                if buffer:
                    self._knowledge_cache[current_section] = "\n".join(buffer)
                
                # Start new section
                section_code = match.group(1) # E3
                section_name = match.group(2) # Walls...
                current_section = f"{section_code} {section_name}"
                buffer = [line]
                logger.info(f"Found section: {current_section}")
            else:
                buffer.append(line)
        
        # Save last section
        if buffer:
            self._knowledge_cache[current_section] = "\n".join(buffer)

        logger.info(f"Parsed {len(self._knowledge_cache)} sections.")

    def get_section(self, key_contains: str) -> str:
        """
        Returns the knowledge text for a specific key (fuzzy match).
        """
        key_lower = key_contains.lower()
        
        # Exact match logic or fuzzy find
        matches = []
        for k, v in self._knowledge_cache.items():
            if key_lower in k.lower():
                matches.append(v)
        
        if not matches:
            return "No specific RICS standard found for this section."
        
        return "\n---\n".join(matches)

    def list_sections(self) -> List[str]:
        return list(self._knowledge_cache.keys())

# Example Usage to test
if __name__ == "__main__":
    loader = KnowledgeLoader()
    print("Available Sections:", loader.list_sections())
    print("\n--- TEST: E3 Walls ---\n")
    print(loader.get_section("E3 Walls")[:500])
