import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AIEngine:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        genai.configure(api_key=self.api_key)
        
        # Mandate from Constitution: Use Gemini 3 Flash
        self.model_name = os.getenv("GEMINI_MODEL_ID", "gemini-3.0-flash-001")
        
        self.generation_config = {
            "temperature": 0.2, # Low temperature for factual reporting (RICS standard)
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }
        
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
             HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
             HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )

    def _load_knowledge_base(self) -> str:
        """
        Loads the RICS standards from the text file.
        In a production environment (Gemini 1.5 Pro/Flash), this would be a Cached Content ID.
        Here we inject it as context to simulate the "Expert" behavior.
        """
        kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base", "rics_standards.txt")
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "RICS Standards Knowledge Base not found."

    async def generate_report_section(self, system_prompt: str, user_content: List[Any], use_rag: bool = True) -> str:
        """
        Generates a section of the report.
        user_content: can be a list containing text strings and PIL Images.
        """
        try:
            full_system_prompt = system_prompt
            
            if use_rag:
                knowledge = self._load_knowledge_base()
                full_system_prompt = f"""
                You are an Expert RICS Chartered Surveyor.
                
                ### KNOWLEDGE BASE (RICS STANDARDS - LEVEL 3):
                {knowledge}
                
                ### INSTRUCTIONS:
                {system_prompt}
                """

             # Add system prompt as the first part of the conversation or context
            chat = self.model.start_chat(history=[
                {"role": "user", "parts": [full_system_prompt]},
                {"role": "model", "parts": ["Understood. I will act as a RICS Level 3 Chartered Surveyor using the provided standards."]}
            ])
            
            response = chat.send_message(user_content)
            return response.text
            
        except Exception as e:
            return f"AI Error: {str(e)}"

    def check_connection(self) -> bool:
        try:
            # Simple ping
            response = self.model.generate_content("Ping")
            return response.text is not None
        except Exception as e:
            print(f"Connection Check Failed: {e}")
            return False
