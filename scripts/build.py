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

def build_windows(arch):
    print(f"Building for Windows {arch}...\n")
    compilePath = rel_path(f"build/windows/{arch}")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-DDRACO_TINY_DECODE_SHARED_LIB=ON",
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

def build_mac():
    print("Building for Mac...\n")
    arch = "x64" if platform.machine() == "x86_64" else "arm64"
    compilePath = rel_path(f"build/mac/{arch}")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-DDRACO_TINY_DECODE_SHARED_LIB=ON",
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
    dstPath = f"build/OUT/runtimes/osx-{arch}/native/libdraco_tiny_dec.dylib"
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(srcPath, dstPath)

def build_uwp(arch):
    print(f"Building for UWP {arch}...\n")
    compilePath = rel_path(f"build/uwp/{arch}")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-DDRACO_TINY_DECODE_SHARED_LIB=ON",
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

def build_wasm(EmscriptenSDKPath):
    print("Building for WebAssembly...\n")
    emsdk_env = os.path.abspath(os.path.join(EmscriptenSDKPath, "emsdk_env.bat"))
    subprocess.run([emsdk_env])
    os.environ["EMSCRIPTEN"] = abspath(os.path.join(EmscriptenSDKPath, "upstream", "emscripten"))

    toolchainFile = abspath(f"{EmscriptenSDKPath}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake")
    crosscompilingEmulator = abspath(f"{EmscriptenSDKPath}/node/20.18.0_64bit/bin/node.exe")
    compilePath = rel_path("build/wasm")
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-GNinja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DDRACO_TINY_DECODE_SHARED_LIB=ON",
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
    dstPath = rel_path("build/OUT/runtimes/browser-wasm/draco_tiny_dec.a")
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(srcPath, dstPath)

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

        "-DDRACO_TINY_DECODE_SHARED_LIB=ON"
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


parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("--emscripten_sdk", help = "Path to the Emscripten SDK install dir")
parser.add_argument("--android_ndk", help = "Path to the Android NDK install dir")
parser.add_argument("--ninja_path", help = "Path to the ninja executable")
args = parser.parse_args()

ninjaExePath = args.ninja_path

if os.name == 'nt':
    build_windows("Win32")
    build_windows("x64")
elif platform.system() == 'Darwin':
    build_mac()

#build_uwp("Win32")
#build_uwp("x64")
#build_uwp("ARM")
#build_uwp("ARM64")

if args.emscripten_sdk:
    build_wasm(args.emscripten_sdk)

if args.android_ndk:
    if not "JAVA_HOME" in os.environ:
        java_path = abspath("openjdk")
        os.environ["JAVA_HOME"] = java_path
    build_android(args.android_ndk, "arm64-v8a", "arm64")
    build_android(args.android_ndk, "armeabi-v7a", "arm")
    build_android(args.android_ndk, "x86", "x86")
    build_android(args.android_ndk, "x86_64", "x64")