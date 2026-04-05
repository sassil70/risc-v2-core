
import urllib.request
import re

# TARGET: Audit Server #2 (Port 8006)
SESSION_ID = "c96caac1-027d-4b77-9c00-ae710194e260"
URL = f"http://localhost:8006/api/reports/{SESSION_ID}"

def check_criteria(html, name, regex, critical=False):
    found = bool(re.search(regex, html, re.IGNORECASE))
    icon = "PASS" if found else "FAIL"
    if not found and critical: icon = "CRITICAL FAIL"
    print(f"[{icon}] {name}")
    return found

def main():
    print("=== DIGITAL SURVEYOR: USER ACCEPTANCE TEST ===")
    print(f"Target: {URL}\n")
    
    try:
        with urllib.request.urlopen(URL) as res:
            html = res.read().decode('utf-8')
    except Exception as e:
        print(f"CRITICAL: System Down - {e}")
        return

    score = 0
    max_score = 100
    
    # 1. LEGAL & BRANDING (30 Points)
    print("--- 1. Legal & Branding ---")
    if check_criteria(html, "RICS Logo or Reference", r"RICS"): score += 10
    if check_criteria(html, "Report Title (Building Survey)", r"Building Survey Report"): score += 10
    # Disclaimer search (flexible match)
    if check_criteria(html, "Liability Disclaimer", r"liability|risk|contract", critical=True): 
        score += 10
    else:
        print("   >> WARNING: Missing Disclaimer exposes Surveyor to legal risk!")

    # 2. STRUCTURE (30 Points)
    print("\n--- 2. Report Structure (RICS Level 3) ---")
    if check_criteria(html, "Section D: Outside", r"Section D.*Outside"): score += 10
    if check_criteria(html, "Section E: Inside", r"Section E.*Inside"): score += 10
    if check_criteria(html, "Section F: Services", r"Section F.*Services"): score += 10

    # 3. CONTENT & EVIDENCE (40 Points)
    print("\n--- 3. Content & Evidence ---")
    # Count images
    img_count = len(re.findall(r"<img", html))
    print(f"[INFO] Visual Evidence Found: {img_count} Items")
    
    if img_count > 5: 
        score += 20
        print("[PASS] Sufficient Visual Evidence")
    elif img_count > 0:
        score += 10
        print("[WARN] Minimal Visual Evidence")
    else:
        print("[FAIL] NO VISUAL EVIDENCE - Report is effectively blank.")
        
    # Check for Defect Ratings (1, 2, 3 or traffic lights)
    if check_criteria(html, "Condition Ratings", r"Condition Rating|Risk"): 
        score += 20
    else:
        print("[FAIL] No Condition Ratings found.")

    print("\n" + "="*40)
    print(f"COMMERCIAL VIABILITY SCORE: {score}/100")
    print("="*40)
    
    if score >= 80:
        print("VERDICT: ACCEPTED for Release.")
    elif score >= 50:
        print("VERDICT: CONDITIONAL PASS (Requires Data).")
    else:
        print("VERDICT: REJECTED (Not Fit for Purpose).")

if __name__ == "__main__":
    main()
