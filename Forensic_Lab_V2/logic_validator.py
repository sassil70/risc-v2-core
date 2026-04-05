import json
import sys
import os

class LogicValidator:
    def __init__(self, report_path):
        self.report_path = report_path
        if not os.path.exists(report_path):
            print(f"ERROR: Report not found at {report_path}")
            sys.exit(1)
        with open(report_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
            
    def assert_keyword(self, keyword):
        """
        Ensures a specific engineering term exists in the AI conclusion.
        """
        text = json.dumps(self.data).lower()
        if keyword.lower() in text:
            print(f"  [PASS] Logic Found: '{keyword}'")
            return True
        else:
            print(f"  [FAIL] Logic Missing: '{keyword}'")
            return False

    def validate_scenario_a(self):
        print("\nChecking Scenario A: Shared Manhole / Drainage Fracture")
        keywords = ["drainage", "fracture", "3 (serious)", "corrosion", "trip hazard", "bs en 124"]
        results = [self.assert_keyword(k) for k in keywords]
        return all(results)

    def validate_scenario_b(self):
        print("\nChecking Scenario B: Water Ingress / Leak (Kitchen)")
        keywords = ["leak", "3 (serious)", "saturated", "staining", "efflorescence", "moisture", "damp", "water damage"]
        results = [self.assert_keyword(k) for k in keywords]
        passed_count = sum(1 for r in results if r)
        return passed_count >= 4

    def validate_scenario_c(self):
        print("\nChecking Scenario C: Fire Door Safety / Joinery (Hallway)")
        # Keywords for fire door safety
        keywords = ["fire door", "smoke seal", "intumescent", "clearance", "hinge", "3 (serious)", "bs 476", "fd30"]
        results = [self.assert_keyword(k) for k in keywords]
        
        passed_count = sum(1 for r in results if r)
        success = passed_count >= 3 # Fire safety is high priority
        
        if success:
            print(f"\nSUCCESS: Forensic Logic matches RICS Fire Safety Standards ({passed_count}/8 markers).")
        else:
            print(f"\nWARNING: AI missed critical fire safety indicators.")
        return success

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python logic_validator.py <path_to_report> <scenario_letter>")
        sys.exit(1)
    
    report_path = sys.argv[1]
    scenario = sys.argv[2].lower()
    
    validator = LogicValidator(report_path)
    
    if scenario == "a":
        res = validator.validate_scenario_a()
    elif scenario == "b":
        res = validator.validate_scenario_b()
    elif scenario == "c":
        res = validator.validate_scenario_c()
    else:
        print(f"Unknown scenario: {scenario}")
        sys.exit(1)
        
    if res:
        sys.exit(0)
    else:
        sys.exit(1)
