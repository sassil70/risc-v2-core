import sys
sys.path.append(r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\03_Reporter_Cluster")
from ai_engine import AIEngine
import asyncio

async def test():
    print("Testing AI Engine Connection...")
    try:
        engine = AIEngine()
        print(f"Model: {engine.model_name}")
        
        # Test 1: Simple Ping
        is_connected = engine.check_connection()
        print(f"Connection Check: {'✅ PASS' if is_connected else '❌ FAIL'}")
        
        # Test 2: RAG Loading
        rag_text = engine._load_knowledge_base()
        print(f"RAG Loaded: {len(rag_text)} chars")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test())
