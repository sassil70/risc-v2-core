
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model_name = "models/gemini-3-flash-preview"

async def test():
    print(f"Testing model: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        response = await model.generate_content_async("Hello, format your response as JSON: {\"status\": \"ok\"}")
        print("Response received:")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())
