from fastapi import APIRouter, Depends
from database import db
import google.generativeai as genai
import os

router = APIRouter()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

@router.get("/surveyor/briefing")
async def get_briefing(user_id: str):
    # 1. Get Stats
    # Count pending tasks
    pending_query = """
        SELECT count(*) as count, min(started_at) as next_time 
        FROM sessions 
        WHERE surveyor_id = $1 AND status IN ('scheduled', 'in_progress')
    """
    stats = await db.fetchrow(pending_query, user_id)
    count = stats['count'] if stats else 0
    
    # Get first task address (simulated from Project Client Name or similar) 
    # Since we don't have explicit address column in sessions yet, we use project name or dummy
    # In V6 proposal we said "High St". We will mock this enrichment for now.
    
    # 2. Formulate Message via Logic or AI
    message = ""
    
    # Simple Fallback Logic
    if count == 0:
        message = "Good Morning. Your schedule is clear. Ready to create a new inspection?"
    else:
        # AI Orchestration (If Key exists)
        if api_key:
            try:
                model = genai.GenerativeModel('gemini-pro') # Or 3.0-flash
                prompt = f"Write a very short, professional morning greeting for a surveyor named Salim. He has {count} inspections today. The weather is rainy. Keep it under 20 words."
                response = model.generate_content(prompt)
                message = response.text
            except Exception as e:
                print(f"Gemini Error: {e}")
                message = f"Good Morning. You have {count} pending inspections today."
        else:
            message = f"Good Morning. You have {count} pending inspections today."

    return {
        "message": message,
        "task_count": count,
        "weather": "Rainy ☔", # Mock for now
        "traffic": "High Traffic 🚗" # Mock for now
    }
