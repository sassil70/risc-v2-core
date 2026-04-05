import os
import google.generativeai as genai

# Setup Gemini
genai.configure(api_key="AIzaSyC0CQ-L_yuBaVDftsNV56FQZUwUr_3ohKo")

pdf_path = "/Users/SalimBAssil/Documents/AntiGravity_Core_Vault_v2026/04_Source_Code/RICS_KNOWLEDGE/knowdgggg/Sample-Home-Survey-Level-3-Report.pdf"

print("Uploading PDF to Gemini for Graphical Analysis...")
try:
    sample_file = genai.upload_file(pdf_path, mime_type="application/pdf")
    
    model = genai.GenerativeModel("gemini-1.5-pro-latest") # Use 1.5 Pro or similar for strong multimodal PDF support
    
    prompt = """
    You are an expert Frontend Developer and RICS Surveyor.
    Analyze the attached official RICS Home Survey Level 3 Report visually.
    I need you to describe in extreme detail its GRAPHICAL LAYOUT and DESIGN so I can recreate it in HTML/CSS for a Playwright PDF generator.
    Pay close attention to:
    1. The cover page (colors, logos location, font sizes).
    2. The headers and footers on every page (legal notes, page numbers).
    3. The Condition Rating (1, 2, 3) visual indicators (e.g., Green, Amber, Red boxes or icons). Provide the exact hex codes if possible.
    4. Typography (Serif vs Sans-Serif used, line spacing).
    5. Table layouts.
    
    Output a detailed CSS architecture plan based strictly on what you see in the document's graphics.
    """
    
    response = model.generate_content([sample_file, prompt])
    print("\n--- GEMINI GRAPHICAL ANALYSIS ---\n")
    print(response.text)
    
except Exception as e:
    print(f"Error: {e}")
