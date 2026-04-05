import os
import logging
from typing import List, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Load env from parent directory (Brain Cluster root)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiService")

class GeminiService:
    _instance = None
    
    # Target Model: Gemini 3.1 Flash (Upgraded)
    MODEL_NAME = os.getenv("GEMINI_MODEL_KEY", "gemini-3.1-flash")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.critical("GOOGLE_API_KEY not found in environment variables.")
            raise ValueError("GOOGLE_API_KEY is missing.")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.MODEL_NAME)
            logger.info(f"Gemini Service initialized with Legacy SDK. Target: {self.MODEL_NAME}")
        except Exception as e:
            logger.critical(f"Failed to initialize GenAI Client: {e}")
            raise e

    async def analyze_evidence(self, 
                             images_paths: List[str], 
                             audio_path: Optional[str], 
                             prompt_text: str) -> str:
        """
        Multimodal Analysis using Legacy SDK (Works with Gemini 3).
        """
        contents = []
        
        # 1. Add Text Prompt
        contents.append(prompt_text)
        
        # 2. Add Images (PIL or Path)
        for path in images_paths:
            if os.path.exists(path):
                try:
                    # Legacy SDK handles paths directly? No, usually PIL images or File API.
                    # Best practice for Legacy SDK: Upload to File API or use PIL.
                    # Creating a Part from bytes is tricky in legacy high-level API.
                    # We will use the File API for robustness with Large contexts.
                    f = genai.upload_file(path)
                    contents.append(f)
                    logger.info(f"Uploaded image: {path} -> {f.uri}")
                except Exception as e:
                    logger.error(f"Failed to load image {path}: {e}")
        
        # 3. Add Audio
        if audio_path and os.path.exists(audio_path):
            try:
                # Upload audio to File API
                f = genai.upload_file(audio_path)
                contents.append(f)
                logger.info(f"Uploaded audio: {audio_path} -> {f.uri}")
            except Exception as e:
                logger.error(f"Failed to load audio {audio_path}: {e}")
        
        # 4. Generate Content
        try:
            logger.info(f"Sending payload to {self.MODEL_NAME}...")
            
            config = genai.GenerationConfig(
                temperature=0.2,
                candidate_count=1,
                response_mime_type="application/json"
            )

            response = self.model.generate_content(
                contents,
                generation_config=config
            )
            
            logger.info("Response received.")
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini Generation Error: {e}")
            return '{"error": "AI Processing Failed", "details": "' + str(e) + '"}'

# Singleton Accessor
def get_gemini_service():
    return GeminiService()
