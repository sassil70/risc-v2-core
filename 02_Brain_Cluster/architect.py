import google.generativeai as genai
import os
import json
import asyncio
import time
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY not found in env.")

genai.configure(api_key=api_key)

# The Model - Gemini 3 Flash Preview (User Specified)
MODEL_NAME = os.getenv("GEMINI_MODEL_KEY", "gemini-3-flash-preview")

from services.prompt_engine import get_prompt_engine

# --- PROMPTS ---
prompt_engine = get_prompt_engine()

def get_stage_1_prompt():
    return prompt_engine.render_prompt("architect/stage_1_extraction.j2", {})

def get_stage_2_prompt():
    return prompt_engine.render_prompt("architect/stage_2_standardization.j2", {})

def get_stage_3_prompt():
    return prompt_engine.render_prompt("architect/stage_3_contextualization.j2", {})

async def refine_room_report(current_report: dict, voice_observation: str):
    """
    Refines an existing room report JSON using a new voice observation.
    """
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = prompt_engine.render_prompt("architect/room_refinement.j2", {
        "current_report_json": json.dumps(current_report, indent=2),
        "voice_observation": voice_observation
    })
    
    response = await model.generate_content_async(prompt)
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)


def clean_json(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[-1]
    elif "```JSON" in text:
        text = text.split("```JSON")[-1]
    elif "```" in text:
        text = text.split("```")[-1]
        
    if "```" in text:
        text = text.split("```")[0]
        
    return text.strip()

# --- FULL IMPLEMENTATION ---

async def execute_3_stage_pipeline(audio_path, property_type, num_floors):
    print(f"Processing Audio: {audio_path}")
    print(f"Model: {MODEL_NAME}")
    
    try:
        # 1. Upload File
        print(f"   [1.1] Uploading Audio to Gemini...")
        try:
            # Note: v1beta SDK upload_file is synchronous
            audio_file = genai.upload_file(audio_path, mime_type="audio/mp4") 
            print(f"   [1.1] Upload Complete: {audio_file.name}. Waiting for processing...")
            
            # [STRATEGIC FIX] Poll until audio processing is ACTIVE
            while audio_file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
                
            if audio_file.state.name == "FAILED":
                raise ValueError("Gemini Backend failed to process the audio file.")
                
            print(f"\n   [1.1] Audio is ACTIVE and ready.")
        except Exception as e:
             print(f" [ERROR] Audio Upload Failed. Check Internet or MIME Type. Details: {e}")
             raise RuntimeError(f"Gemini Upload Failed: {e}")

        # --- STAGE 1 ---
        print(f"   [1.2] Generating Content (Listening)...")
        model_s1 = genai.GenerativeModel(MODEL_NAME, system_instruction=get_stage_1_prompt())
        
        try:
            # Using synchronous generate_content as typical for file inputs in this SDK version
            # We wrap in asyncio.to_thread if we wanted non-blocking, but for now we need the result.
            prompt = f"Property: {property_type}, {num_floors} Floors. Extract rooms."
            res_s1 = model_s1.generate_content([prompt, audio_file])
            
            raw_json_str = clean_json(res_s1.text)
            print(f"   [1.2] Stage 1 Output Length: {len(raw_json_str)}")
        except Exception as e:
            print(f" [ERROR] Stage 1 Generation Failed: {e}")
            raise RuntimeError(f"Gemini Generation Failed: {e}")

        # --- STAGE 2 ---
        print(f"   [2.0] Standardizing...")
        model_s2 = genai.GenerativeModel(MODEL_NAME, system_instruction=get_stage_2_prompt())
        res_s2 = model_s2.generate_content(f"Standardize: {raw_json_str}")
        std_json_str = clean_json(res_s2.text)
        
        # --- STAGE 3 ---
        print(f"   [3.0] Enriching...")
        model_s3 = genai.GenerativeModel(MODEL_NAME, system_instruction=get_stage_3_prompt())
        res_s3 = model_s3.generate_content(f"Enrich: {std_json_str}")
        final_json_str = clean_json(res_s3.text)
        
        final_json = json.loads(final_json_str)
        
        if "floors" not in final_json and "rooms" in final_json:
            print(" AI returned flat list. Converting to Floors Structure...")
            final_json = {
                "floors": [
                    {
                        "name": "General/Extracted",
                        "rooms": final_json["rooms"]
                    }
                ]
            }
        
        return final_json

    except Exception as e:
        print(f" [CRITICAL] Architect Pipeline Failed: {e}")
        # Fallback to avoid 500 in App
        return {
            "error": str(e),
            "fallback_mode": True,
            "floors": [{"name": "Ground Floor (AI Error)", "rooms": []}] 
        }

# Expose main function
async def generate_floor_plan(audio_path, property_type, num_floors):
    return await execute_3_stage_pipeline(audio_path, property_type, num_floors)
