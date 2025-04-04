import os
import io
import sys
import subprocess
import shutil
import time
from zipfile import ZipFile
import argparse
abspath = os.path.abspath

def pip_install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print('{}{}'.format(subindent, f))

pip_install("requests")
import requests # we need requests in order to download emsdk and ninja

# Save the current working directory
original_dir = os.getcwd()

def download_and_extract(url, dst = "."):
    with requests.get(url, stream=True) as r:
        with ZipFile(io.BytesIO(r.raw.read()), "r") as zip_ref:
            zip_ref.extractall(dst)

def tmp_path(path):
    """Return the path to the temporary directory."""
    return abspath(os.path.join(os.path.dirname(__file__), f"../tmp/{path}"))

# --- Emscripten ---
def install_deps_emscripten():
    print("Installing Emscripten...\n")
    emsdk_url = "https://github.com/emscripten-core/emsdk/archive/master.zip"
    download_and_extract(emsdk_url, ".")
    os.rename(
        tmp_path("emsdk-master"),
        tmp_path("emsdk"))

    # Run Emscripten commands
    emsdk_bat = tmp_path("emsdk/emsdk.bat")
    os.system(f"{emsdk_bat} update")
    os.system(f"{emsdk_bat} install 4.0.6")
    os.system(f"{emsdk_bat} activate 4.0.6")

# --- Ninja ---
def install_deps_ninja():
    print("Installing Ninja...\n")
    ninja_url = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-win.zip"
    download_and_extract(ninja_url, ".")
    
# --- Android SDK/NDK ---
def install_deps_android_ndk():
    print("Installing Android NDK...\n")

    if not "JAVA_HOME" in os.environ:
        java_path = tmp_path("openjdk")
        os.environ["JAVA_HOME"] = java_path
        os.environ["PATH"] = f"{java_path};{os.environ['PATH']}"
        subprocess.Popen(["java.exe", "-version"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    shutil.rmtree(tmp_path("android-tools"), ignore_errors=True)
    url = "https://dl.google.com/android/repository/commandlinetools-win-13114758_latest.zip"
    download_and_extract(url, tmp_path(""))
    os.rename(tmp_path("cmdline-tools"), tmp_path("android-tools"))

    sdkmanager_path = tmp_path("android-tools/bin/sdkmanager.bat")

    sdk_path = tmp_path("android_sdk")
    needToAcceptLicenses = True
    if needToAcceptLicenses:
        process = subprocess.Popen([sdkmanager_path, f"--licenses", f"--sdk_root={sdk_path}"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        process.stdin.write(b"y\n" * 10)
        try:
            process.stdin.flush()
        except Exception as e:
            print(f"Error flushing stdin: {e}")
        out, err = process.communicate()

    process = subprocess.Popen([sdkmanager_path, "--install", f"--sdk_root={sdk_path}", "ndk;26.3.11579264"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = process.communicate()
    print(out.decode())
    list_files(sdk_path)

# --- Java ---
def install_deps_java():
    print("Installing OpenJDK...\n")

    long_path = tmp_path("openlogic-openjdk-21.0.6+7-windows-x64")
    short_path = tmp_path("openjdk")
    shutil.rmtree(long_path, ignore_errors=True)
    shutil.rmtree(short_path, ignore_errors=True)
    
    url = "https://builds.openlogic.com/downloadJDK/openlogic-openjdk/21.0.6+7/openlogic-openjdk-21.0.6+7-windows-x64.zip"
    download_and_extract(url, tmp_path(""))
    os.rename(long_path, short_path)
    
# --- Install dependencies ---
def install_deps(emscripten, ninja, android_ndk, java):
    try:
        # Define the temporary folder path
        tmp_folder = tmp_path("")
        os.makedirs(tmp_folder, exist_ok=True)
        os.chdir(tmp_folder)

        if java:
            install_deps_java()
        if emscripten:
            install_deps_emscripten()
        if ninja:
            install_deps_ninja()
        if android_ndk:
            install_deps_android_ndk()
    finally:
        # Restore the original working directory
        os.chdir(original_dir)

def main():
    parser = argparse.ArgumentParser(description="Install dependencies for the project.")
    parser.add_argument("--emscripten", action="store_true", help="Install Emscripten dependencies.")
    parser.add_argument("--ninja", action="store_true", help="Install Ninja build system.")
    parser.add_argument("--android_ndk", action="store_true", help="Install Android SDK/NDK.")
    parser.add_argument("--java", action="store_true", help="Install OpenJDK.")
    parser.add_argument("--all", action="store_true", help="Install all dependencies.")
    args = parser.parse_args()

    install_deps(
        emscripten = args.emscripten or args.all,
        ninja = args.ninja or args.all,
        android_ndk = args.android_ndk or args.all,
        java = args.java or args.all
    )

if __name__ == "__main__":
    main()
