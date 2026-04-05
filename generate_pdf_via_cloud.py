import os
import re
import base64
import requests
import markdown

API_URL = "https://risc-v2-reporter-926489000848.europe-west1.run.app/api/v2/report/compile"
MD_FILE = "/Users/SalimBAssil/Documents/AntiGravity_Core_Vault_v2026/04_Source_Code/RISC_V2_Core_System/Surveyors_Beta_Testing_Guide_Pro.md"
OUTPUT_PDF = os.path.expanduser("~/Desktop/Expert_Surveyor_Guide.pdf")

def read_file():
    with open(MD_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def inject_base64_images(md_text):
    # Regex to find absolute paths
    pattern = r'!\[.*?\]\((/Users/SalimBAssil/[^\)]+)\)'
    
    def replacer(match):
        img_path = match.group(1)
        try:
            with open(img_path, 'rb') as img_f:
                b64_data = base64.b64encode(img_f.read()).decode('utf-8')
                ext = img_path.split('.')[-1].lower()
                mime = 'image/png' if ext == 'png' else 'image/jpeg'
                return f'<img src="data:{mime};base64,{b64_data}" class="hero-img" />'
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")
            return match.group(0)
            
    return re.sub(pattern, replacer, md_text)

def main():
    print("1. Reading Markdown...")
    raw_md = read_file()
    
    print("2. Packaging Images as Base64...")
    md_with_images = inject_base64_images(raw_md)
    
    print("3. Transforming to HTML & Mermaid...")
    html_content = markdown.markdown(md_with_images, extensions=['tables'])
    
    # Advanced styling and Mermaid loader specially optimized for Playwright Cloud Run
    final_html = f"""
    <!DOCTYPE html>
    <html lang="ar">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&family=Inter:wght@400;600&display=swap');
            body {{ font-family: 'Inter', 'Tajawal', sans-serif; line-height: 1.6; color: #333; padding: 30px; }}
            h1 {{ color: #1a365d; text-align: center; border-bottom: 2px solid #ebf8ff; padding-bottom: 10px; }}
            h2 {{ color: #2b6cb0; margin-top: 30px; }}
            .hero-img {{ width: 100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 20px 0; }}
            .note {{ background-color: #ebf8ff; padding: 15px; border-left: 5px solid #3182ce; border-radius: 4px; margin: 15px 0; }}
            .ar-text {{ direction: rtl; text-align: right; font-family: 'Tajawal', sans-serif; }}
            .mermaid {{ display: flex; justify-content: center; margin: 30px 0; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            th {{ background-color: #f2f2f2; text-align: left; }}
        </style>
        <!-- Load Mermaid explicitly for rendering -->
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', () => {{
                // Parse pre codes designated as mermaid manually
                document.querySelectorAll('code.default').forEach(block => {{
                    if(block.textContent.includes('graph ') || block.textContent.includes('journey')) {{
                        let div = document.createElement('div');
                        div.className = 'mermaid';
                        div.textContent = block.textContent;
                        block.parentNode.replaceWith(div);
                    }}
                }});
                mermaid.initialize({{ startOnLoad: true, theme: 'base' }});
            }});
        </script>
    </head>
    <body>
        <div style="font-size: 1.2rem; display: flex; flex-direction: column; gap: 15px">
        {html_content}
        </div>
    </body>
    </html>
    """
    
    print("4. Transmitting to Cloud Run Reporter API...")
    try:
        req = requests.post(
            API_URL, 
            json={"html_content": final_html, "filename": "Guide_Cloud.pdf"}
        )
        if req.status_code == 200:
            with open(OUTPUT_PDF, 'wb') as f:
                f.write(req.content)
            print(f"✅ Success! Beautiful PDF saved to: {OUTPUT_PDF}")
        else:
            print(f"❌ Server Error: {req.status_code}")
            print(req.text)
    except Exception as e:
        print(f"❌ Network Error: {e}")

if __name__ == "__main__":
    main()
