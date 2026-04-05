from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import uuid
import google.generativeai as genai
from dotenv import load_dotenv
from ai_engine import AIEngine
from services.pdf_compiler import compile_to_pdf

# Load Secrets
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
gemini_model = os.getenv("GEMINI_MODEL_ID", "gemini-3.0-flash-001")

if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY not found in reporter .env")

# Configure AI
genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI(title="RISC V2 Reporter - AI Engine")

class AnalyzeRequest(BaseModel):
    room_id: str
    force_reanalysis: bool = False

@app.get("/")
def read_root():
    return {
        "status": "Reporter Cluster Online", 
        "model": gemini_model
    }

@app.post("/api/v2/ai/analyze/room")
async def analyze_room(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Triggers the Gemini 3 Flash analysis for a specific room.
    """
    engine = AIEngine()
    
    # 1. Fetch Data (Mocked for now, normally would query AlloyDB via Brain or Direct)
    # Simulator: We assume the 'room_id' maps to some context we know or we accept data directly (for now simply using hardcoded context for the test sequence)
    
    # logic: In real system, we select * from media_assets where room_id = ...
    # For this simulation, we will construct a prompt assuming we found "1 photo of a cracked wall".
    
    system_prompt = "You are a specialized RICS surveyor. Analyze the finding."
    user_content = [f"Room ID: {request.room_id}. Finding: Severe structural cracking observed above lintel. Suggest remediation."]
    
    # 2. Call AI (Async)
    # We await here to return the result immediately for the test, 
    # but in production this might be a background task updating a job status.
    try:
        response_text = await engine.generate_report_section(system_prompt, user_content)
        return {
            "status": "completed", 
            "room_id": request.room_id, 
            "model": engine.model_name,
            "ai_report": response_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RewriteRequest(BaseModel):
    text: str
    context: str = "formal engineering report"

@app.post("/api/v2/ai/rewrite")
async def rewrite_text(request: RewriteRequest):
    """
    Rewrites text using Gemini 3 Flash.
    """
    engine = AIEngine()
    
    system_prompt = "You are an expert RICS surveyor editor. Rewrite the following text to be more professional, concise, and technically accurate. Maintain the original meaning."
    user_content = [f"Context: {request.context}", f"Original Text: {request.text}"]
    
    try:
        response_text = await engine.generate_report_section(system_prompt, user_content)
        return {"rewritten_text": response_text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CompileRequest(BaseModel):
    html_content: str
    filename: str = "RICS_Final_Report.pdf"

@app.post("/api/v2/report/compile")
async def compile_final_pdf(request: CompileRequest):
    """
    Receives aggregated HTML chunks from Brain/Frontend and compiles
    them into a strict RICS formatted PDF using Playwright Chromium.
    """
    output_dir = "/app/output"
    os.makedirs(output_dir, exist_ok=True)
    
    unique_id = str(uuid.uuid4())[:8]
    output_file = os.path.join(output_dir, f"{unique_id}_{request.filename}")
    
    try:
        pdf_path = await compile_to_pdf(request.html_content, output_file)
        
        # In a real microservice, we might return the URL or stream the file.
        # For simplicity, we return the file directly to the caller.
        return FileResponse(
            path=pdf_path, 
            filename=request.filename, 
            media_type="application/pdf"
        )
    except Exception as e:
        print(f"PDF Compilation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF Compilation failed: {str(e)}")
