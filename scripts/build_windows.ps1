# Build FaceLES.exe on Windows, then a double-click installer if Inno Setup is present.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    py -3 -m venv (Join-Path $Root ".venv")
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
}

Write-Host "Installing dependencies…"
& $Python -m pip install -q -r (Join-Path $Root "requirements.txt") "pyinstaller>=6.0"

Write-Host "Building FaceLES.exe…"
Remove-Item -Recurse -Force (Join-Path $Root "build") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $Root "dist\FaceLES") -ErrorAction SilentlyContinue
& $Python -m PyInstaller --noconfirm --clean (Join-Path $Root "packaging\FaceLES.spec")

$Exe = Join-Path $Root "dist\FaceLES\FaceLES.exe"
if (-not (Test-Path $Exe)) {
    throw "Build failed: $Exe not found"
}
Write-Host "Built: $Exe"

$Iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($Iscc) {
    Write-Host "Building FaceLES-Setup.exe…"
    & $Iscc (Join-Path $Root "packaging\windows\FaceLES.iss")
    Write-Host "Installer: $(Join-Path $Root 'dist\FaceLES-Setup.exe')"
} else {
    Write-Host "Inno Setup not found — skipping installer."
    Write-Host "Employees can still zip dist\FaceLES and run FaceLES.exe inside that folder."
    Write-Host "To make a Setup.exe: install Inno Setup 6, then re-run this script."
}
