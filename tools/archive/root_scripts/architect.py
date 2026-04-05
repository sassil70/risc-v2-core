import google.generativeai as genai
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY not found in env.")

genai.configure(api_key=api_key)

# The Model - Gemini 2.0 Flash for Speed + Multimodal
MODEL_NAME = os.getenv("GEMINI_MODEL_KEY", "gemini-2.0-flash-exp")

# --- PROMPTS ---

# STAGE 1: RAW EXTRACTION
SYSTEM_PROMPT_STAGE_1 = """
You are a Transcriptionist. 
Listen to the audio and extract the list of rooms and areas mentioned.
Do NOT try to rename or standardize them yet. Just capture what was said.
Output JSON: {"rooms": [{"raw_name": "Living room downstairs", "type": "general"}, ...]}
"""

# STAGE 2: RICS STANDARDIZATION (THE NAMING AUTHORITY)
SYSTEM_PROMPT_STAGE_2 = """
You are a Senior RICS Surveyor acting as a "Terminologist".
Your task is to take a list of RAW room names and convert them into STRANDARD RICS UNIQUE IDENTIFIERS.

RULES:
1. Names must include Location/Floor if ambiguous (e.g., "G_Living_Room", "F1_Master_Bedroom").
2. Use spacing or underscores for readability.
3. Separate "External" and "Services" clearly.
4. Ensure EVERY room has a unique name.

INPUT: Raw JSON List.
OUTPUT: JSON {"rooms": [{"id": "unique_id", "name": "RICS_Standard_Name", "type": "wet/general/external/services"}]}
"""

# STAGE 3: CONTEXTUALIZATION (SMART TAGS)
SYSTEM_PROMPT_STAGE_3 = """
You are an Inspection Architect.
For each room provided, generate the specific RICS Inspection Contexts (Tags).
For "External" and "Services", use the standard fixed lists if applicable, otherwise generate relevant ones.

INPUT: RICS Standardized Room List.
OUTPUT: Final JSON with this EXACT structure:
{
  "floors": [
    {
       "name": "Ground Floor",
       "rooms": [
          { "id": "...", "name": "...", "type": "...", "contexts": [...] }
       ]
    },
    {
       "name": "First Floor",
        "rooms": []
    }
  ]
}
RULES:
1. You MUST group rooms into 'floors' array.
2. Do NOT return a flat 'rooms' list.
3. Use the room names (G_, F1_) to decide the grouping.
"""


async def list_files_for_simulation():
    """Helper to list available simulation files"""
    # implementation detail 
    pass

async def generate_floor_plan_v2(audio_path: str, property_type: str, num_floors: int):
    """
    Executes the 3-Stage Rocket: Extraction -> Standardization -> Contextualization
    """
    model = genai.GenerativeModel(MODEL_NAME)
    
    try:
        # --- STAGE 1: EXTRACTION ---
        print(f"🚀 STAGE 1: Raw Extraction from {audio_path}...")
        
        # In a real scenario, we upload the audio file.
        # For this logic test, we might mock the audio input if it's a text simulation, 
        # but here we assume audio is passed.
        
        # Uploading file...
        uploaded_file = genai.upload_file(audio_path, mime_type="audio/mp4") # Or m4a depending on file
        
        prompt_1 = f"Property: {property_type}, {num_floors} Floors. Extract rooms."
        
        # We need to construct the chain manually as we want distinct steps
        # Optimization: One long conversation or separate calls? Separate is safer for structured output.
        
        # ... logic to call Gemini Stage 1 ...
        # response_1 = ...
        # raw_data = json.loads(response_1.text)
        
        # --- STAGE 2: STANDARDIZATION ---
        print("🚀 STAGE 2: RICS Standardization...")
        # prompt_2 = f"Standardize this list: {json.dumps(raw_data)}"
        # response_2 = ...
        # standard_data = json.loads(response_2.text)
        
        # --- STAGE 3: CONTEXTS ---
        print("🚀 STAGE 3: Context Enrichment...")
        # prompt_3 = f"Add tags to: {json.dumps(standard_data)}"
        # response_3 = ...
        # final_plan = json.loads(response_3.text)
        
        # return final_plan
        return {} # Placeholder for the full implementation below

    except Exception as e:
        print(f"Architect V2 Error: {e}")
        return None

# --- FULL IMPLEMENTATION (Replacing the mocked flow above) ---

async def execute_3_stage_pipeline(audio_path, property_type, num_floors):
    print(f"Processing Audio: {audio_path}")
    
    # 1. Upload File
    audio_file = genai.upload_file(audio_path, mime_type="audio/mp4") # Ensure mime type is correct
    
    # --- STAGE 1 ---
    model_s1 = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT_STAGE_1)
    res_s1 = model_s1.generate_content([f"Property: {property_type}, {num_floors} Floors.", audio_file])
    raw_json_str = clean_json(res_s1.text)
    print(f"Stage 1 Output: {raw_json_str}")
    
    # --- STAGE 2 ---
    model_s2 = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT_STAGE_2)
    res_s2 = model_s2.generate_content(f"Standardize: {raw_json_str}")
    std_json_str = clean_json(res_s2.text)
    print(f"Stage 2 Output: {std_json_str}")
    
    # --- STAGE 3 ---
    model_s3 = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT_STAGE_3)
    res_s3 = model_s3.generate_content(f"Enrich: {std_json_str}")
    final_json_str = clean_json(res_s3.text)
    
    final_json = json.loads(final_json_str)
    
    # [ROBUSTNESS FIX] Ensure 'floors' structure even if AI returns flat 'rooms'
    if "floors" not in final_json and "rooms" in final_json:
        print("⚠️ AI returned flat list. Converting to Floors Structure...")
        # Create a default Ground Floor and put everything there for now, 
        # or try to parse names. Simple fallback:
        final_json = {
            "floors": [
                {
                    "name": "General/Extracted",
                    "rooms": final_json["rooms"]
                }
            ]
        }
    
    return final_json


def clean_json(text):
    if text.startswith("```json"):
        return text.replace("```json", "").replace("```", "").strip()
    if text.startswith("```"):
        return text.replace("```", "").strip()
    return text.strip()

# Expose main function
async def generate_floor_plan(audio_path, property_type, num_floors):
    return await execute_3_stage_pipeline(audio_path, property_type, num_floors)
