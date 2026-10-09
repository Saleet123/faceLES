# -*- mode: python ; coding: utf-8 -*-
"""Ubuntu / Linux onedir bundle for FaceLES. Keep this folder together when you copy it."""

import os
import sys

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

SPECDIR = os.path.dirname(os.path.abspath(SPEC))
ROOT = os.path.dirname(SPECDIR)

datas, binaries, hiddenimports = [], [], []
# Collect OpenCV fully (LBPH lives in cv2.face). Let PySide6 hooks follow real imports
# so unused Qt3D/QML/Charts modules stay out of the Ubuntu folder.
for pkg in ("shiboken6", "cv2"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

binaries += collect_dynamic_libs("cv2")

datas += [
    (os.path.join(ROOT, "haarcascade_frontalface_default.xml"), "."),
    (os.path.join(ROOT, "assets"), "assets"),
]
profile = os.path.join(ROOT, "profile_pic.jpg")
if os.path.isfile(profile):
    datas.append((profile, "."))

hiddenimports += [
    "cv2.face",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtXml",
    "PySide6.QtNetwork",
]
if sys.platform.startswith("linux"):
    hiddenimports.append("PySide6.QtDBus")

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(SPECDIR, "pyi_rth_faceles.py")],
    excludes=["tkinter", "matplotlib", "pytest", "unittest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FaceLES",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=os.path.join(ROOT, "assets", "icons", "app.ico")
    if os.path.isfile(os.path.join(ROOT, "assets", "icons", "app.ico"))
    else os.path.join(ROOT, "assets", "icons", "app.svg"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FaceLES",
)
