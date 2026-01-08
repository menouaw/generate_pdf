import os

MSYS2_DLL_DIR = r"C:\msys64\mingw64\bin"

if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(MSYS2_DLL_DIR)

os.environ["PATH"] = MSYS2_DLL_DIR + ";" + os.environ.get("PATH", "")