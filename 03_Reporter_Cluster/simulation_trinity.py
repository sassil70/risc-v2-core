import sys
import os
import asyncio
import hashlib

# Add paths to sys to allow cross-module imports for simulation
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, "02_Brain_Cluster")) 
sys.path.append(os.path.join(project_root, "03_Reporter_Cluster"))

# Import from Brain
try:
    from forensic import ForensicValidator
except ImportError:
    print("❌ Failed to import Brain Cluster modules. Check paths.")
    sys.exit(1)

# Import from Reporter
try:
    from ai_engine import AIEngine
except ImportError:
    print("❌ Failed to import Reporter Cluster modules.")
    sys.exit(1)

async def run_trinity_simulation():
    print("\nSTARTING TRINITY COMPLETED SIMULATION")
    print("=======================================")

    # --- Step 1: Cluster 1 (The Witness) ---
    print("\n[Step 1] The Witness (Mobile)")
    print("   - Action: Capturing Evidence and creating Signed Package...")
    
    evidence_data = b"PHOTO_OF_CRACKED_LINTEL_DATA_BINARY"
    # Create mock file
    evidence_path = "mock_evidence.bin"
    with open(evidence_path, "wb") as f:
        f.write(evidence_data)

    # Calculate Hash (Mobile Logic Simulation)
    mobile_hash = hashlib.sha256(evidence_data).hexdigest()
    print(f"   - Generated Hash: {mobile_hash[:8]}...")
    print("   - Status: Package Ready for Upload.")

    # --- Step 2: Cluster 2 (The Brain) ---
    print("\n[Step 2] The Brain (Sync & Verify)")
    print("   - Action: Receiving Package and Validating Integrity...")
    
    server_calculated_hash = ForensicValidator.calculate_file_hash(evidence_path)
    
    if server_calculated_hash == mobile_hash:
        print(f"   - Server Hash:    {server_calculated_hash[:8]}...")
        print("   MATCH CONFIRMED. Evidence Accepted into Immutable Log.")
    else:
        print("   INTEGRITY FAILURE. Sync Rejected.")
        return

    # --- Step 3: Cluster 3 (AI Reporter) ---
    print("\n[Step 3] AI Reporter (Gemini 3 Flash)")
    print("   - Action: Analyzing Evidence for RICS Compliance...")
    
    try:
        engine = AIEngine()
        print(f"   - Model Connected: {engine.model_name}")
        
        system_ops = "You are a Senior RICS Building Surveyor."
        user_ops = [
            f"Evidence Hash: {mobile_hash}",
            "Finding: High resolution image shows vertical cracking above window lintel, approx 3mm width.",
            "Task: Diagnose the defect and suggest RICS-compliant remediation."
        ]
        
        print("   - Sending Request to Gemini...")
        report = await engine.generate_report_section(system_prompt=system_ops, user_content=user_ops)
        
        print("\n[Generated RICS Report Section]")
        print("-----------------------------------")
        print(report)
        print("-----------------------------------")
        print("TRINITY INTEGRATION SUCCESSFUL.")
        
    except Exception as e:
        print(f"   AI Failure: {e}")

    # Cleanup logic simulation
    if os.path.exists(evidence_path):
        os.remove(evidence_path)

if __name__ == "__main__":
    # Fix for Windows loop policy if needed, but simple run usually works
    asyncio.run(run_trinity_simulation())
