import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KnowledgeLoader")

class RISCKnowledgeLoader:
    def __init__(self, cache_path: str):
        self.cache_path = Path(cache_path)
        if not self.cache_path.exists():
            raise FileNotFoundError(f"Knowledge cache not found at: {cache_path}")

    def load_and_parse(self) -> Dict[str, str]:
        """
        Loads the raw text and segments it into RICS Sections (A-L).
        Returns a dictionary {Section_Title: Section_Content}
        """
        try:
            raw_text = self.cache_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Failed to read cache file: {e}")
            return {}

        # Clean basic noise (Page numbers, headers)
        clean_text = self._clean_noise(raw_text)
        
        # Segment by RICS Sections using Regex
        # Pattern looks for "SECTION E" or "E roof" style headers often found in the dump
        # Based on RICS Structure: A, B, C, D, E, F, G, H, I, J, K, L, M
        
        sections = {}
        
        # Regex to find typical Section Headers in the dump
        # Example from file: "E ROOF PROCESS" or just "E1 Roof Structure"
        # We will use a flexible splitter for capital letter headers
        
        # 1. Define main sections we care about for RAG
        target_sections = [
            "A About the inspection",
            "B Safety",
            "C The Property",
            "D Outside",
            "E Inside",
            "F Services",
            "G Grounds",
            "H Issues",
            "I Risks",
            "J Energy",
            "K Surveyor"
        ]
        
        current_section = "PREAMBLE"
        buffer = []
        
        for line in clean_text.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # Check if line is a major header
            is_header = False
            for sec in target_sections:
                # detection logic: Line starts with "D Outside" (case insensitive)
                if line.upper().startswith(sec.upper().split()[0] + " "): 
                     # e.g. "D " from "D Outside"
                     # Check if the rest matches loosely
                     if sec.split()[1].upper() in line.upper():
                         # Save previous
                         if buffer:
                             sections[current_section] = "\n".join(buffer)
                         
                         # Start new
                         current_section = sec
                         buffer = []
                         is_header = True
                         break
            
            if not is_header:
                buffer.append(line)
        
        # Save last section
        if buffer:
            sections[current_section] = "\n".join(buffer)
            
        logger.info(f"Loaded {len(sections)} sections from Knowledge Base.")
        return sections

    def _clean_noise(self, text: str) -> str:
        """
        Removes OCR artifacts, page numbers, and repetitive footers.
        """
        # Remove lines that are just numbers (Page numbers)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove RICS standard footer if present
        text = re.sub(r'RICS Home Survey – Level 3', '', text, flags=re.IGNORECASE)
        
        # Remove repeating dates (e.g. 27/10/202527/10/2025...)
        text = re.sub(r'(\d{2}/\d{2}/\d{4})+', '', text)
        
        # Remove lines with isolated small numbers (like list indices that lost text)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        return text

# Usage Example
if __name__ == "__main__":
    import sys
    # Default path for testing
    default_path = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\Smart_Surveyor_NextGen\01_Control_Module\control_backend\knowledge_cache.txt"
    loader = RISCKnowledgeLoader(default_path)
    data = loader.load_and_parse()
    
    for sec, content in data.items():
        print(f"--- SECTION: {sec} ({len(content)} chars) ---")
        print(content[:200].replace('\n', ' ') + "...")
