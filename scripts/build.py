import os
import sys
import subprocess
import argparse
import shutil
import platform
from pathlib import Path
abspath = os.path.abspath

# AndroidNDKPath = "C:/APPS/android-ndk-r26d"
# EmscriptenSDKPath = "C:/APPS/emsdk"

archTransltionStr = {"Win32":"x86", "x64":"x64", "ARM":"arm", "ARM64":"arm64"}

def rel_path(path):
    return abspath(os.path.join(os.path.dirname(__file__), f"../{path}"))

# --- Windows ---
def build_windows(arch):
    print(f"Building for Windows {arch}...\n")
    compilePath = rel_path(f"build/windows/{arch}")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-DDRACO_TINY_LIB=ON",
        "-DDRACO_TINY_LIB_SHARED=ON",
        "-A", arch
    ]
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return

    build_cmd = ["cmake", "--build", compilePath, "--config", "Release",]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return

    archStr = archTransltionStr[arch]

    srcPath = os.path.join(compilePath, "Release/draco_tiny_dec.dll")
    dstPath = rel_path(f"build/OUT/runtimes/win-{archStr}/native/draco_tiny_dec.dll")
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(srcPath, dstPath)

# --- MacOS ---
def build_mac():
    print("Building for Mac...\n")
    arch = "x64" if platform.machine() == "x86_64" else "arm64"
    compilePath = rel_path(f"build/mac/{arch}")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-DDRACO_TINY_LIB=ON",
        "-DDRACO_TINY_LIB_SHARED=ON",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return
    
    build_cmd = ["cmake", "--build", compilePath, ]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return
    
    srcPath = os.path.join(compilePath, "libdraco_tiny_dec.dylib")
    dstPath = f"build/OUT/runtimes/osx-{arch}/native/draco_tiny_dec.dylib"
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(srcPath, dstPath)

# --- IOS ---
def build_ios_arm64(ios_platform):
    ios_platforms = {
        "OS64" : "ios-arm64",
        "SIMULATORARM64": "iossimulator-arm64",
    }
    if not ios_platform in ios_platforms.keys():
        print(f"Invalid iOS platform({ios_platform}). Valid values are {ios_platforms.keys()}")
        return
    runtimesFolderName = ios_platforms[ios_platform]

    print(f"Building for {runtimesFolderName} ...\n")
    compilePath = rel_path(f"build/{runtimesFolderName}")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-G", "Xcode",
        f'-DCMAKE_TOOLCHAIN_FILE={rel_path("cmake/toolchains/ios.toolchain.cmake")}',
        f"-DPLATFORM={ios_platform}",
        "-DDRACO_TINY_LIB=ON",
        "-DDRACO_TINY_LIB_SHARED=OFF",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return
    
    build_cmd = ["cmake", "--build", compilePath, "--config", "Release"]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return
    

    # amalgamete static library
    compilePath = os.path.join(compilePath,
        f"Release-iphoneos" if ios_platform == "OS64" else "Release-iphonesimulator")
    dracoPath = os.path.join(compilePath, "libdraco.a")
    tinyDecPath = os.path.join(compilePath, "libdraco_tiny_dec.a")
    amalgamatedPath = os.path.join(compilePath, "libdraco_tiny_dec_amalgamated.a")
    amalgamate_cmd = ["libtool", "-static", "-o", amalgamatedPath, tinyDecPath, dracoPath]
    result = subprocess.run(amalgamate_cmd)
    if result.returncode != 0:
        print("Failed to amalgamate the static libraries.")
        return

    # copy to OUT folder
    dstPath = rel_path(f"build/OUT/runtimes/{runtimesFolderName}/native/libdraco_tiny_dec.a")
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(amalgamatedPath, dstPath)

# --- UWP ---
def build_uwp(arch):
    print(f"Building for UWP {arch}...\n")
    compilePath = rel_path(f"build/uwp/{arch}")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-DDRACO_TINY_LIB=ON",
        "-DDRACO_TINY_LIB_SHARED=ON",
        "-DCMAKE_SYSTEM_NAME=WindowsStore",
        "-DCMAKE_SYSTEM_VERSION=10.0",
        "-DCMAKE_C_COMPILER_WORKS=FALSE",
            # this flag is very weird, there doesn't seem to be much documentation about it online.
            # However, it seems that, without it, CMake complains that it can't find the C compiler.
            # I discovered this flag in Evergine's Bullet project
        "-A", arch
    ]
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return
    
    build_cmd = ["cmake", "--build", compilePath, "--config", "Release", ]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return
    
    archStr = archTransltionStr[arch]

    srcPath = os.path.join(compilePath, "Release/draco_tiny_dec.dll")
    dstPath = rel_path(f"build/OUT/runtimes/win-{archStr}/nativeassets/uap10.0/draco_tiny_dec.dll")
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(srcPath, dstPath)

# --- Wasm ---
def build_wasm(EmscriptenSDKPath):
    print("Building for WebAssembly...\n")
    emsdk_env = os.path.abspath(os.path.join(EmscriptenSDKPath, "emsdk_env.bat"))
    subprocess.run([emsdk_env])
    os.environ["EMSCRIPTEN"] = abspath(os.path.join(EmscriptenSDKPath, "upstream", "emscripten"))

    toolchainFile = abspath(f"{EmscriptenSDKPath}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake")
    nodeDir = abspath(f"{EmscriptenSDKPath}/node")
    nodeVersion = os.listdir(nodeDir)[0]
    crosscompilingEmulator = os.path.join(nodeDir, nodeVersion, "/bin/node.exe")
    compilePath = rel_path("build/wasm")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-GNinja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DDRACO_TINY_LIB=ON",
        "-DDRACO_TINY_LIB_SHARED=ON",
        f"-DCMAKE_TOOLCHAIN_FILE={toolchainFile}",
        f"-DCMAKE_CROSSCOMPILING_EMULATOR={crosscompilingEmulator}",
        "-DDRACO_WASM=ON"
    ]
    if ninjaExePath:
        ninjaExePath_absolute = abspath(ninjaExePath)
        cmake_cmd.append(f"-DCMAKE_MAKE_PROGRAM={ninjaExePath_absolute}")
        
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return

    build_cmd = ["cmake", "--build", compilePath]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return
    
    srcPath = abspath(os.path.join(compilePath, "libdraco_tiny_dec.a"))
    dstPath = rel_path("build/OUT/runtimes/browser-wasm/native/draco_tiny_dec.a")
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(srcPath, dstPath)

# --- Android ---
def build_android(AndroidNDKPath, abi, abiFolder):
    print(f"Building for Android {abi}...\n")
    compilePath = rel_path(f"build/android/{abiFolder}")
    toolchainFile = abspath(os.path.join(AndroidNDKPath, "build/cmake/android.toolchain.cmake"))
    cmake_cmd = [
        "cmake", ".",
        "-B", compilePath,
        "-G", "Ninja",
        f"-DCMAKE_TOOLCHAIN_FILE={toolchainFile}",
        "-DANDROID_TOOLCHAIN=clang",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_CXX_FLAGS_RELEASE=-O3",
        "-DANDROID_TOOLCHAIN=clang",
        f"-DANDROID_ABI={abi}",
        "-DANDROID_PLATFORM=android-24",
        "-DANDROID_STL=c++_static",
        "-DDRACO_TINY_LIB=ON",
        "-DDRACO_TINY_LIB_SHARED=ON",
    ]
    if ninjaExePath:
        ninjaExePath_absolute = abspath(ninjaExePath)
        cmake_cmd.append(f"-DCMAKE_MAKE_PROGRAM={ninjaExePath_absolute}")

    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return

    build_cmd = ["cmake", "--build", compilePath]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return

    llvm_strip = abspath(os.path.join(AndroidNDKPath, "toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip"))
    strip_cmd = [
        llvm_strip,
        "-s", os.path.join(compilePath, "libdraco_tiny_dec.so")
    ]
    result = subprocess.run(strip_cmd)
    if result.returncode != 0:
        return
    
    srcPath = abspath(os.path.join(compilePath, "libdraco_tiny_dec.so"))
    dstPath = rel_path(f"build/OUT/runtimes/android-{abiFolder}/native/draco_tiny_dec.so")
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(srcPath, dstPath)

# --- Linux ---
def build_linux(arch):
    print(f"Building for Linux {arch}...\n")
    compilePath = rel_path(f"build/linux/{arch}")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-DDRACO_TINY_LIB=ON",
        "-DDRACO_TINY_LIB_SHARED=ON",
        "-DCMAKE_BUILD_TYPE=Release",
        "-GNinja",
    ]
    if platform.machine() == "x86_64" and arch == "ARM64":
        cmake_cmd += [ # crosscompiling
            "-DCMAKE_SYSTEM_PROCESSOR=aarch64",
            "-DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc",
            "-DCMAKE_CXX_COMPILER=aarch64-linux-gnu-g++",
        ]

    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return
    
    build_cmd = ["cmake", "--build", compilePath, "--config", "Release",]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return
    
    archStr = archTransltionStr[arch]

    srcPath = os.path.join(compilePath, "libdraco_tiny_dec.so")
    dstPath = rel_path(f"build/OUT/runtimes/linux-{archStr}/native/draco_tiny_dec.so")
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(srcPath, dstPath)

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("--emscripten_sdk", help = "Path to the Emscripten SDK install dir")
parser.add_argument("--android_ndk", help = "Path to the Android NDK install dir")
parser.add_argument("--ninja_path", help = "Path to the ninja executable")
parser.add_argument("--ios", action="store_true", help = "Build for iOS arm64")
args = parser.parse_args()

ninjaExePath = args.ninja_path

if os.name == 'nt':
    build_windows("Win32")
    build_windows("x64")
elif platform.system() == 'Darwin':
    build_mac()
    if args.ios:
        build_ios_arm64("OS64")
        build_ios_arm64("SIMULATORARM64")
elif platform.system() == 'Linux':
    build_linux("x64")
    build_linux("ARM64")

#build_uwp("Win32")
#build_uwp("x64")
#build_uwp("ARM")
#build_uwp("ARM64")

if args.emscripten_sdk:
    build_wasm(args.emscripten_sdk)

if args.android_ndk:
    if not "JAVA_HOME" in os.environ:
        java_path = abspath("openjdk/bin")
        os.environ["JAVA_HOME"] = java_path
        os.environ["PATH"] = f"{java_path};{os.environ['PATH']}"
    build_android(args.android_ndk, "arm64-v8a", "arm64")
    build_android(args.android_ndk, "armeabi-v7a", "arm")
    build_android(args.android_ndk, "x86", "x86")
    build_android(args.android_ndk, "x86_64", "x64")