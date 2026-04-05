import logging
import os
import sys
from typing import List, Optional, Dict

# Ensure parent directory is in path to import knowledge_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .gemini_service import get_gemini_service
from knowledge_loader import RISCKnowledgeLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGService")

from .prompt_engine import get_prompt_engine

class RISCRAGService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RISCRAGService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # 1. Initialize Gemini
        self.gemini = get_gemini_service()
        
        # 2. Init Prompt Engine
        self.prompt_engine = get_prompt_engine()
        
        # 3. Initialize Knowledge Base
        # Path assumes we are in services/ subdir, matching ../knowledge_loader.py logic
        # But we need the absolute path to cache. Ideally passed via config.
        # Fallback to relative hardcoded path for Phase 1 velocity.
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Adjust path to where knowledge_cache.txt actually lives
        # From tools: Documents/Smart_Inspection_Project/Smart_Surveyor_NextGen/01_Control_Module/control_backend/knowledge_cache.txt
        # But we might want to move it to Brain Cluster.
        # For now, let's use the one we tested in knowledge_loader.py
        
        self.kb_path = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\Smart_Surveyor_NextGen\01_Control_Module\control_backend\knowledge_cache.txt"
        
        try:
            self.loader = RISCKnowledgeLoader(self.kb_path)
            self.sections = self.loader.load_and_parse()
            logger.info("RAG Service Initialized (Knowledge Loaded).")
        except Exception as e:
            logger.error(f"RAG Service Failed to load Knowledge: {e}")
            self.sections = {}

    async def forensic_analysis(self, 
                              context_scope: str, 
                              images: List[str], 
                              audio_path: Optional[str]) -> str:
        """
        Performs a dynamic RAG analysis.
        context_scope: e.g. "Outside", "Inside", "Services"
        """
        
        # 1. Select Knowledge Context
        knowledge_text = ""
        scope_map = {
            "outside": "D Outside",
            "inside": "E Inside",
            "services": "F Services",
            "risks": "I Risks",
            "grounds": "G Grounds"
        }
        
        key = scope_map.get(context_scope.lower())
        if key and key in self.sections:
            knowledge_text += f"\n--- RICS SECTION ({key}) ---\n{self.sections[key]}\n"
        
        if "I Risks" in self.sections:
             knowledge_text += f"\n--- GENERAL RISKS (REF) ---\n{self.sections['I Risks'][:2000]}...\n"
             
        # 2. Render Prompt via Engine
        # Determine Template File
        template_name = "base_surveyor.j2" # Default
        if context_scope.lower() == "outside":
            template_name = "context_outside.j2"
        elif context_scope.lower() == "inside":
            template_name = "context_inside.j2"
            
        system_instruction = self.prompt_engine.render_prompt(
            template_name=template_name,
            context_data={"rics_knowledge_context": knowledge_text}
        )
        
        # 3. Call Gemini
        result = await self.gemini.analyze_evidence(
            images_paths=images,
            audio_path=audio_path,
            prompt_text=system_instruction
        )
        
        return result

def get_rag_service():
    return RISCRAGService()
