import asyncio
from ai_engine import AIEngine
import os

async def experiment():
    print("Starting Gemini 3 Flash Experiment...")
    
    try:
        engine = AIEngine()
        print(f"Engine Initialized. Target Model: {engine.model_name}")
        
        print("Pinging Google AI Servers...")
        if engine.check_connection():
            print("Connection Successful!")
        else:
            print("Connection Failed. Check API Key or Internet.")
            return

        print("\nSending Test Prompt:")
        prompt = "Describe the role of a RICS Building Surveyor in one sentence."
        print(f"   Input: '{prompt}'")
        
        response = await engine.generate_report_section(
            system_prompt="You are a helper.",
            user_content=[prompt]
        )
        
        print(f"\nResponse (Gemini 3 Flash):")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
    except Exception as e:
        print(f"\nExperiment Failed: {e}")

if __name__ == "__main__":
    asyncio.run(experiment())
