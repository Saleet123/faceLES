FaceLES for Windows
===================

This Ubuntu machine cannot produce a .exe. Build on a Windows PC (or GitHub Actions).

On a Windows PC, from the FaceLES folder:

  scripts\build_windows.bat

That runs scripts\build_windows.ps1 (venv, PyInstaller, optional Inno Setup).

That creates:

  dist\FaceLES\FaceLES.exe     (keep the whole FaceLES folder)
  dist\FaceLES-Setup.exe       (if Inno Setup 6 is installed)

Give employees FaceLES-Setup.exe. They double-click it, then open FaceLES
from the Start menu or Desktop shortcut.

Login until you change settings:
  username: saleet
  password: 123

Logs and the enrolled face are stored in:
  %APPDATA%\FaceLES\

Without Inno Setup, zip dist\FaceLES and tell people to unzip and
double-click FaceLES.exe. Do not send FaceLES.exe by itself.

Optional installer:
  https://jrsoftware.org/isinfo.php
