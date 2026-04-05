import fitz
import json
import os
import pprint

# The precise RICS section headers to locate in T.pdf
TARGET_HEADERS = [
    "D1  Chimney stacks",
    "D2  Roof coverings",
    "D3  Rainwater pipes and gutters",
    "E1  Ceilings",
    "E2  Walls and partitions",
    "E3  Floors",
    "E4  Internal doors",
    "E5  Built-in fittings (built-in kitchen and other fittings, not including appliances)",
    "F1  Electricity",
    "F2  Gas/oil",
    "F3  Water",
    "F4  Heating",
    "F5  Water heating"
]

def map_coordinates():
    template_path = os.path.join(os.path.dirname(__file__), "..", "..", "03_Reporter_Cluster", "assets", "reference_templates", "T.pdf")
    template_path = os.path.abspath(template_path)
    
    if not os.path.exists(template_path):
        print(f"File not found: {template_path}")
        return

    doc = fitz.open(template_path)
    mapping = {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block.get("type") == 0:  # Text block
                text = ""
                box = block["bbox"]
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text += span.get("text", "")
                
                text = text.strip()
                for header in TARGET_HEADERS:
                    # RICS template headers often span multiple spans or have weird spacing
                    # So we use a basic prefix match
                    if text.startswith(header.split("  ")[0]) and header.split("  ")[1] in text:
                        mapping[header] = {
                            "page": page_num,
                            "bbox": box,
                            "estimated_start_y": box[3] + 20 # 20 points below the header
                        }
                        
    print("Found coordinates:")
    pprint.pprint(mapping)

if __name__ == "__main__":
    map_coordinates()
