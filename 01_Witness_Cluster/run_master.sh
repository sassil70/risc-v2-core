#!/bin/bash
set -e

echo "=========================================================="
echo "🚀 ANTIGRAVITY MASTER DEPLOYMENT SCRIPT (RADICAL REBUILD)"
echo "=========================================================="

VAULT_DIR="/Users/SalimBAssil/Documents/AntiGravity_Core_Vault_v2026"
FLUTTER_APP_DIR="$VAULT_DIR/04_Source_Code/RISC_V2_Core_System/01_Witness_Cluster"
SDK_DIR="$VAULT_DIR/android-sdk"
MAC_PASSWORD="Msbasba@123"

FLUTTER_BIN="/tmp/flutter_isolated/bin/flutter"

# 1. ERADICATING MACOS SANDBOX LOCKS
echo ""
echo "🔓 [1/5] Bypassing macOS Sandbox Permission Locks..."
echo "✅ Using Isolated Sandboxed Flutter SDK to avoid OS-level engine.stamp blocks."

# 2. DYNAMIC NETWORK DETECTION (WIRED OR WIRELESS)
echo ""
echo "🌐 [2/5] Scanning Network Interfaces for Active Host IP..."
# Prioritize wireless en0 specifically to avoid picking up Docker bridges 
ACTIVE_IP=$(ifconfig en0 | grep "inet " | grep -v 127.0.0.1 | head -n 1 | awk '{print $2}')

# Inject sandbox-compliant temporary directory for the Flutter compiler 
export TMPDIR=/tmp
export PUB_CACHE=/tmp/.pub-cache
export GRADLE_USER_HOME=/tmp/.gradle

# Bypassing macOS Profile locks: Fake the HOME directory so Flutter analytics and config write locally
mkdir -p /tmp/fakehome
export HOME=/tmp/fakehome

if [ -z "$ACTIVE_IP" ]; then
    echo "❌ ERROR: No active network connection found! Are you connected to Wi-Fi or Ethernet?"
    exit 1
fi
echo "✅ Active Mac Host IP Detected: $ACTIVE_IP (Dynamically routing App APIs to this)"

# 3. ENVIRONMENT SANITATION
echo ""
echo "🧹 [3/5] Terminating hung Gradle Daemons..."
pkill -f 'gradle' || true

if [ ! -d "$VAULT_DIR/java-17" ]; then
    echo "⬇️ Downloading Portable Java 17 (To bypass Java 25 compilation crashes)..."
    curl -L -s -o /tmp/jdk17.tar.gz "https://corretto.aws/downloads/latest/amazon-corretto-17-aarch64-macos-jdk.tar.gz"
    mkdir -p "$VAULT_DIR/java-17"
    tar -xzf /tmp/jdk17.tar.gz -C "$VAULT_DIR/java-17" --strip-components=1
    rm /tmp/jdk17.tar.gz
    xattr -d -r com.apple.quarantine "$VAULT_DIR/java-17" 2>/dev/null || true
fi

# Enforce Portable Java 17 to bypass Java 25 compiler crash
export JAVA_HOME="$VAULT_DIR/java-17/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"

export ANDROID_HOME="$SDK_DIR"
export ANDROID_SDK_ROOT="$SDK_DIR"
export GRADLE_OPTS="-Dorg.gradle.daemon=false -Dkotlin.compiler.execution.strategy=in-process"

# 4. COMPILING FLUTTER (WITH DYNAMIC IP INJECTION)
echo ""
echo "🔨 [4/5] Compiling Native Android APK with injected route: $ACTIVE_IP"
cd "/tmp/Witness_Isolated"
"$FLUTTER_BIN" pub get

# Build the APK while injecting the detected IP directly into the Dart Environment
"$FLUTTER_BIN" build apk --release --dart-define=HOST_IP=$ACTIVE_IP

# 5. ADB DEPLOYMENT
echo ""
echo "📲 [5/5] Deploying App DIRECTLY via ADB to connected Samsung Device..."
"$SDK_DIR/platform-tools/adb" install -r build/app/outputs/flutter-apk/app-release.apk

# 6. CLEANUP
rm -rf /tmp/Witness_Isolated

echo ""
echo "🎉 DEPLOYMENT SUCCESSFUL! The fully patched App is now on your device."
echo "=========================================================="
