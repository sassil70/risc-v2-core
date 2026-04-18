import os
import subprocess
from mcp.server.fastmcp import FastMCP

# Initialize the Flutter DevOps MCP Server
# This acts as the bridge granting the AI full unrestricted OS terminal access.
mcp = FastMCP("Flutter-DevOps-Bridge")

# Core Paths (Updated to the new Developer neutral zone)
VAULT_DIR = os.path.expanduser("~/Developer/AntiGravity_Core_Vault_v2026")
FLUTTER_PROJECT = os.path.join(VAULT_DIR, "04_Source_Code", "RISC_V2_Core_System", "01_Witness_Cluster")
FLUTTER_BIN = os.path.join(VAULT_DIR, "flutter", "bin", "flutter")

@mcp.tool()
def build_flutter_apk() -> str:
    """Build a release APK for Android using the native custom build script."""
    try:
        script_path = os.path.join(FLUTTER_PROJECT, "build_android_native.sh")
        # Run in unrestricted host mode
        result = subprocess.run(["bash", script_path], cwd=FLUTTER_PROJECT, capture_output=True, text=True, check=True)
        return f"✅ Android APK Build Success:\n{result.stdout[-800:]}"
    except subprocess.CalledProcessError as e:
        return f"❌ Android Build Failed (Code {e.returncode}):\n{e.stderr}\n\nSTDOUT:\n{e.stdout}"

@mcp.tool()
def deploy_ios_archive() -> str:
    """Trigger the iOS signed build and export process using the desktop script."""
    try:
        script_path = os.path.expanduser("~/Desktop/build_ios_signed.sh")
        if not os.path.exists(script_path):
            return "❌ Missing script: ~/Desktop/build_ios_signed.sh"
            
        result = subprocess.run(["bash", script_path], cwd=os.path.join(FLUTTER_PROJECT, "ios"), capture_output=True, text=True, check=True)
        return f"✅ iOS IPA Exported Successfully:\n{result.stdout[-800:]}"
    except subprocess.CalledProcessError as e:
        return f"❌ iOS Build Failed (Code {e.returncode}):\n{e.stderr}\n\nSTDOUT:\n{e.stdout}"

@mcp.tool()
def run_flutter_tests() -> str:
    """Run all Flutter unit and forensic tests in the Witness Cluster."""
    try:
        result = subprocess.run([FLUTTER_BIN, "test"], cwd=FLUTTER_PROJECT, capture_output=True, text=True)
        # Even if tests fail, we return the output to the AI to analyze, so we don't throw an error.
        return f"Test Results:\n{result.stdout}"
    except Exception as e:
        return f"❌ Test executor unhandled exception: {str(e)}"

@mcp.tool()
def ping_sandbox() -> str:
    """Verify the MCP bridge connection is alive and running with unrestricted access."""
    curr_dir = os.getcwd()
    return f"🟢 MCP Bridge Active!\nCurrent Working Directory: {curr_dir}\nSandbox Restrictions Passed!"

if __name__ == "__main__":
    # Start the standard IO bridge for the AI Model Context Protocol
    mcp.run()
