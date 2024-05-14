import os
import sys
import subprocess
import argparse
from pathlib import Path

# AndroidNDKPath = "C:/APPS/android-ndk-r26d"
# EmscriptenSDKPath = "C:/APPS/emsdk"

def build_windows():
    outPath = "build/windows"
    cmake_cmd = [
        "cmake",
        "-B", outPath,
        "-DDRACO_TINY_DECODE_SHARED_LIB=ON",
    ]
    result = subprocess.run(cmake_cmd)
    if result.returncode != 0:
        return

    build_cmd = ["cmake", "--build", outPath, "--config", "Release",]
    subprocess.run(build_cmd)

def build_uwp(arch):
    outPath = f"build/uwp/{arch}"
    cmake_cmd = [
        "cmake",
        "-B", outPath,
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
    
    build_cmd = ["cmake", "--build", outPath, "--config", "Release", ]
    subprocess.run(build_cmd)

def build_wasm(EmscriptenSDKPath):
    outPath = "build/wasm"
    cmake_cmd = [
        "cmake",
        "-B", outPath,
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

    build_cmd = ["cmake", "--build", outPath]
    subprocess.run(build_cmd)


def build_android(AndroidNDKPath, abi, abiFolder):
    outPath = f"build/android/{abiFolder}"
    cmake_cmd = [
        "cmake", ".",
        "-B", outPath,
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

    build_cmd = ["cmake", "--build", outPath]
    subprocess.run(build_cmd)

    strip_cmd = [
        f"{AndroidNDKPath}/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip",
        "-s", f"{outPath}/libdraco_tiny_dec.so"
    ]
    subprocess.run(strip_cmd)

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