#!/bin/bash
set -e

echo "🚀 Starting Native Android SDK Provisioning & APK Build on Mac..."

VAULT_DIR="/Users/SalimBAssil/Documents/AntiGravity_Core_Vault_v2026"
LOCAL_DEPS_DIR="$VAULT_DIR/04_Source_Code/RISC_V2_Core_System/01_Witness_Cluster/.build_deps"

if [ ! -d "$LOCAL_DEPS_DIR/java-17" ]; then
    echo "⬇️ Downloading Portable Java 17 (To bypass Java 25 compilation crashes)..."
    curl -L -s -o /tmp/jdk17.tar.gz "https://corretto.aws/downloads/latest/amazon-corretto-17-aarch64-macos-jdk.tar.gz"
    mkdir -p "$LOCAL_DEPS_DIR/java-17"
    tar -xzf /tmp/jdk17.tar.gz -C "$LOCAL_DEPS_DIR/java-17" --strip-components=1
    rm /tmp/jdk17.tar.gz
    # Remove macOS quarantine attribute so Java runs without prompting user
    xattr -d -r com.apple.quarantine "$LOCAL_DEPS_DIR/java-17" 2>/dev/null || true
fi

export JAVA_HOME="$LOCAL_DEPS_DIR/java-17/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"

SDK_DIR="$LOCAL_DEPS_DIR/android-sdk"
FLUTTER_APP_DIR="$VAULT_DIR/04_Source_Code/RISC_V2_Core_System/01_Witness_Cluster"

mkdir -p "$SDK_DIR"
cd "$SDK_DIR"

if [ ! -f "cmdline-tools/latest/bin/sdkmanager" ]; then
    echo "⬇️ Downloading Android Command Line Tools..."
    curl -o cmdline-tools.zip "https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip"
    unzip -q cmdline-tools.zip
    rm cmdline-tools.zip
    mkdir -p cmdline-tools/latest
    mv cmdline-tools/bin cmdline-tools/lib cmdline-tools/source.properties cmdline-tools/latest/ 2>/dev/null || true
fi

echo "✅ Accepting Licenses and Installing SDK Platforms..."
yes | ./cmdline-tools/latest/bin/sdkmanager --licenses > /dev/null
./cmdline-tools/latest/bin/sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"

echo "⬇️ Injecting NDK 25.0.2 directly (Bypassing Java issues)..."
if [ ! -d "ndk/25.0.2" ]; then
    mkdir -p ndk
    curl -L -o ndk.zip "https://dl.google.com/android/repository/android-ndk-r25c-darwin.zip"
    unzip -q ndk.zip -d ndk/
    mv ndk/android-ndk-r25c ndk/25.0.2
    rm ndk.zip
    # Fix NDK revision parsing crash for Gradle
    sed -i '' 's/Pkg.Revision = .*/Pkg.Revision = 25.0.2/' ndk/25.0.2/source.properties
fi

export ANDROID_HOME="$SDK_DIR"
export ANDROID_SDK_ROOT="$SDK_DIR"



echo "🔨 Cleaning and Compiling Native APK (This will take a few minutes)..."

# Terminate any hung background Java/Gradle daemons from the previous frozen run
pkill -f 'gradle' || true

cd "$FLUTTER_APP_DIR"
"$VAULT_DIR/flutter/bin/flutter" clean
"$VAULT_DIR/flutter/bin/flutter" pub get

echo "⚙️ Forcing synchronous, non-daemon build to bypass MacOS IPC locks..."
export GRADLE_OPTS="-Dorg.gradle.daemon=false -Dkotlin.compiler.execution.strategy=in-process"

"$VAULT_DIR/flutter/bin/flutter" build apk --release -v

echo "✅ Build Process Complete!"
echo "📲 The new APK is located in build/app/outputs/flutter-apk/app-release.apk"
echo "🎉 To install directly via ADB, run: adb install -r build/app/outputs/flutter-apk/app-release.apk"
