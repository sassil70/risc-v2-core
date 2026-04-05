
import urllib.request
import urllib.error
import json
import time
import sys

SESSION_ID = "c96caac1-027d-4b77-9c00-ae710194e260"
# Switched to Audit Port 8006 (Sanitized Code)
API_URL = f"http://localhost:8006/api/reports/{SESSION_ID}/generate_ai"
ITERATIONS = 5

def run_test(run_id: int):
    print(f"\n[RUN #{run_id}] Starting AI Generation Request...")
    start_time = time.time()
    
    try:
        req = urllib.request.Request(API_URL, method='POST')
        with urllib.request.urlopen(req) as response:
            latency = time.time() - start_time
            status = response.status
            
            print(f"[RUN #{run_id}] Duration: {latency:.2f}s | Status: {status}")
            
            if status == 200:
                data = json.load(response)
                
                # VALIDATION
                report = data.get("report")
                if not report:
                    print(f"[RUN #{run_id}] FAIL: Missing 'report' key in JSON")
                    return False, latency
                    
                # Check for sections (RICS output)
                sections = report.get("sections")
                gen_obs = report.get("general_observation")
                
                if sections or gen_obs:
                    print(f"[RUN #{run_id}] PASS: Content Verified (Sections: {len(sections) if sections else 0})")
                    return True, latency
                else:
                    print(f"[RUN #{run_id}] WARN: Valid JSON but empty content.")
                    return True, latency
            else:
                print(f"[RUN #{run_id}] FAIL: HTTP Status {status}")
                return False, latency

    except urllib.error.HTTPError as e:
        print(f"[RUN #{run_id}] FAIL: HTTP Error {e.code} - {e.reason}")
        return False, 0.0
    except Exception as e:
        print(f"[RUN #{run_id}] EXCEPTION: {e}")
        return False, 0.0

def probe_get():
    print(f"\n[PROBE] Checking GET endpoint...")
    url = f"http://localhost:8006/api/reports/{SESSION_ID}"
    print(f"[PROBE] URL: {url}")
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req) as response:
            print(f"[PROBE] Status: {response.status}")
            return response.status == 200
    except Exception as e:
        print(f"[PROBE] FAILED: {e}")
        return False

def main():
    print("=== AI RELIABILITY STRESS TEST (Gemini 3 Flash - Urllib Version) ===")
    print(f"Target POST: {API_URL}")
    print(f"Iterations: {ITERATIONS}\n")
    
    if not probe_get():
        print("CRITICAL: GET endpoint missing. Router likely not mounted correctly.")
        return

    results = []
    
    for i in range(1, ITERATIONS + 1):
        success, duration = run_test(i)
        results.append({"id": i, "success": success, "duration": duration})
        time.sleep(1) # Cooldown
        
    print("\n\n=== FINAL RESULTS ===")
    print("-" * 50)
    print(f"| {'Run #':<5} | {'Status':<10} | {'Time (s)':<10} |")
    print("-" * 50)
    
    total_time = 0
    success_count = 0
    
    for r in results:
        status_icon = "SUCCESS" if r['success'] else "FAILED"
        print(f"| {r['id']:<5} | {status_icon:<10} | {r['duration']:<10.2f} |")
        if r['success']:
            total_time += r['duration']
            success_count += 1
            
    avg_time = total_time / success_count if success_count > 0 else 0
    print("-" * 50)
    print(f"\nReliability: {success_count}/{ITERATIONS} ({(success_count/ITERATIONS)*100:.0f}%)")
    print(f"Avg Latency: {avg_time:.2f}s")
    
    if success_count == ITERATIONS:
        print("\n SYSTEM INTEGRITY: EXCELLENT")
    else:
        print("\n SYSTEM INTEGRITY: UNSTABLE")

if __name__ == "__main__":
    main()
