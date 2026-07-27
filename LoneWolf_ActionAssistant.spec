# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


datas = [
    ("assistant.html", "."),
    ("index.html", "."),
    ("library.html", "."),
    ("install-books.html", "."),
    ("logo.ico", "."),
    ("assets", "assets"),
    ("data", "data"),
]
binaries = []
hiddenimports = []

for package in ("webview", "websockets", "winpty"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    ["saa_main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lone Wolf Action Assistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # The desktop executable must use the windowed bootloader. On systems
    # where Windows Terminal is the default console host, a console bootloader
    # opens a visible terminal tab even when PyInstaller asks it to hide early.
    # The embedded terminal relaunches this same EXE with --cli inside WinPTY,
    # so the main desktop process needs no separate or visible console.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["logo.ico"],
    version="version_info.txt",
)

# A one-folder build avoids unpacking the full application to a temporary
# _MEI directory on every launch. The installed app still starts from the
# same Lone Wolf Action Assistant.exe entry point.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Lone Wolf Action Assistant",
)
