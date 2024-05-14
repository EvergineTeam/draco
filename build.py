import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path

# AndroidNDKPath = "C:/APPS/android-ndk-r26d"
# EmscriptenSDKPath = "C:/APPS/emsdk"

def build_windows():
    compilePath = "build/windows"
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-DDRACO_TINY_DECODE_SHARED_LIB=ON",
    ]
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return

    build_cmd = ["cmake", "--build", compilePath, "--config", "Release",]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return

    dstPath = "build/OUT/runtimes/win-x64/nativeassets/netstandard2.0/draco_tiny_dec.dll"
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(f"{compilePath}/Release/draco_tiny_dec.dll", dstPath)

def build_uwp(arch):
    compilePath = f"build/uwp/{arch}"
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
    
    archStr = {"Win32":"x86", "x64":"x64", "ARM":"arm", "ARM64":"arm64"}[arch]

    dstPath = f"build/OUT/runtimes/win-{archStr}/nativeassets/uap10.0/draco_tiny_dec.dll"
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(f"{compilePath}/Release/draco_tiny_dec.dll", dstPath)

def build_wasm(EmscriptenSDKPath):
    compilePath = "build/wasm"
    cmake_cmd = [
        "cmake",
        "-B", compilePath,
        "-GNinja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DDRACO_TINY_DECODE_SHARED_LIB=ON",
        f"-DCMAKE_TOOLCHAIN_FILE={EmscriptenSDKPath}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake",
        f"-DCMAKE_CROSSCOMPILING_EMULATOR={EmscriptenSDKPath}/node/16.20.0_64bit/bin/node.exe",
        "-DDRACO_WASM=ON"
    ]
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return

    build_cmd = ["cmake", "--build", compilePath]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return
    
    dstPath = "build/OUT/build/wasm/draco_tiny_dec.a"
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(f"{compilePath}/libdraco_tiny_dec.a", dstPath)

def build_android(AndroidNDKPath, abi, abiFolder):
    compilePath = f"build/android/{abiFolder}"
    cmake_cmd = [
        "cmake", ".",
        "-B", compilePath,
        "-G", "Ninja",
        f"-DCMAKE_TOOLCHAIN_FILE={AndroidNDKPath}/build/cmake/android.toolchain.cmake",
        "-DANDROID_TOOLCHAIN=clang",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_CXX_FLAGS_RELEASE=-O3",
        "-DANDROID_TOOLCHAIN=clang",
        f"-DANDROID_ABI={abi}",
        "-DANDROID_PLATFORM=android-24",
        "-DANDROID_STL=c++_static",

        "-DDRACO_TINY_DECODE_SHARED_LIB=ON"
    ]
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return

    build_cmd = ["cmake", "--build", compilePath]
    result = subprocess.run(build_cmd)
    if result.returncode != 0:
        return

    strip_cmd = [
        f"{AndroidNDKPath}/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip",
        "-s", f"{compilePath}/libdraco_tiny_dec.so"
    ]
    result = subprocess.run(strip_cmd)
    if result.returncode != 0:
        return
    
    dstPath = f"build/OUT/runtimes/android-{abiFolder}/native/draco_tiny_dec.so"
    os.makedirs(os.path.dirname(dstPath), exist_ok=True)
    shutil.copy2(f"{compilePath}/libdraco_tiny_dec.so", dstPath)


parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("--emscripten_sdk", help = "Path to the Emscripten SDK install dir")
parser.add_argument("--android_ndk", help = "Path to the Android NDK install dir")
args = parser.parse_args()

build_windows()

build_uwp("Win32")
build_uwp("x64")
build_uwp("ARM")
build_uwp("ARM64")

if args.emscripten_sdk:
    build_wasm(args.emscripten_sdk)

if args.android_ndk:
    build_android(args.android_ndk, "arm64-v8a", "arm64")
    build_android(args.android_ndk, "armeabi-v7a", "arm")
    build_android(args.android_ndk, "x86", "x86")
    build_android(args.android_ndk, "x86_64", "x64")