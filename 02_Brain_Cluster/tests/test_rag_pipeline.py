import asyncio
import logging
from services.rag_service import get_rag_service

logging.basicConfig(level=logging.INFO)

async def test_pipeline():
    print("--- STARTING RAG PIPELINE TEST ---")
    
    # 1. Initialize Service
    rag = get_rag_service()
    
    # 2. Define Evidence (Using existing test audio)
    audio_path = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage\sessions\c96caac1-027d-4b77-9c00-ae710194e260\audio_evidence\floor_plan_audio_v1.m4a"
    images = [] # No images for this specific audio test
    
    # 3. Define Context (Simulate user clicking 'Outside')
    context = "outside"
    
    print(f"Testing Context: {context}")
    print(f"Evidence: {audio_path}")
    
    # 4. Run Analysis
    try:
        explanation = await rag.forensic_analysis(
            context_scope=context,
            images=images,
            audio_path=audio_path
        )
        print("\n--- GEMINI 3 RAG RESPONSE (Templated) ---")
        print(explanation)
        print("----------------------------")
        
    except Exception as e:
        print(f"Pipeline Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
