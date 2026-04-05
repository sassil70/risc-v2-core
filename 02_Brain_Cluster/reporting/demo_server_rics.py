"""
RICS A-M Demo Server - Context Aware
Serves Spot Reports mapped to strict RICS sections.
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from reporting.rics_engine import engine

app = FastAPI(title="RICS Context-Aware Demo")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

MOCK_SESSION = {"address": "123 Westminster Abbey, London, SW1"}
MOCK_ANALYSIS = {"summary": "Standard condition.", "rating": 1, "evidence_photos": ["img1.jpg"]}

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RICS Spot Report Generator</title>
        <link rel="stylesheet" href="/static/css/rics_global.css">
        <style>
            body { font-family: 'Inter', sans-serif; padding: 40px; background: #f3f4f6; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 600px; margin: 0 auto; }
            h1 { color: #003366; text-align: center; }
            .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; background: #003366; color: white; text-align: center; text-decoration: none; border-radius: 6px; font-weight: bold; }
            .btn:hover { background: #002244; }
            .btn-wet { background: #0ea5e9; }
            .btn-ext { background: #10b981; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>📄 RICS Spot Generator</h1>
            <p style="text-align: center; color: #666;">Select a context to generate a Compliant Partial Report:</p>
            
            <a href="/generate/Dry" class="btn">🏠 Generate "Dry Room" Report (Section E only)</a>
            <a href="/generate/Wet" class="btn btn-wet">🚿 Generate "Wet Room" Report (Section E + F)</a>
            <a href="/generate/Exterior" class="btn btn-ext">🌳 Generate "Exterior" Report (Section D + G)</a>
            <hr>
            <a href="/experiment" class="btn" style="background: #e11d48;">🔬 RUN FULL END-TO-END EXPERIMENT (Real Property Data)</a>

        </div>
    </body>
    </html>
    """

@app.get("/experiment", response_class=HTMLResponse)
async def full_experiment():
    import json
    session_path = r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\Smart_Surveyor_NextGen\01_Control_Module\control_backend\sessions\prop_1767289350\session.json"
    with open(session_path, "r", encoding="utf-8") as f:
        session_json = json.load(f)
        
    aggregated_data = engine.aggregate_session_to_rics(session_json)
    
    # Inject evidence for "Visual Excellence"
    for key in ["e_ceilings_list", "e_walls_list"]:
        for i, item in enumerate(aggregated_data.get(key, [])):
            if i < 3:
                 item["photos"] = [f"https://via.placeholder.com/400x300?text=Finding+Photo+{i+1}"]

    session_metadata = {
        "address": "Mirdif Villa - Phase 1 (Real Data Export)",
        "date": "02 February 2026"
    }
    html_content = engine.generate_report(session_metadata, aggregated_data)
    return HTMLResponse(content=html_content)

@app.get("/generate/{context}", response_class=HTMLResponse)
async def generate_spot(context: str):
    """
    Simulate the "Generate Report" button action.
    """
    # 1. Simulate Room Data from JSON
    room_data = {
        "id": f"{context.lower()}_001",
        "name": f"Demo {context} Unit",
        "context": context
    }
    
    # 2. Simulate AI Analysis
    analysis = MOCK_ANALYSIS.copy()
    if context == "Wet":
        analysis["summary"] = "High moisture readings near the shower tray."
        analysis["rating"] = 2
    
    # 3. Router Logic: Map Room -> RICS Sections
    mapped_data = engine.map_room_to_sections(room_data, analysis)
    
    # 4. Generate HTML
    html_content = engine.generate_report(MOCK_SESSION, mapped_data)
    
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    print("Starting RICS Context Demo on http://localhost:8081")
    uvicorn.run(app, host="0.0.0.0", port=8081)
