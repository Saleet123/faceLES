#define MyAppName "FaceLES"
#define MyAppVersion "1.0.0"
#define MyAppExeName "FaceLES.exe"

[Setup]
AppId={{8F3C1A2B-9D64-4E11-A7C0-FACE1E500001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=FaceLES
DefaultDirName={localappdata}\Programs\FaceLES
DefaultGroupName=FaceLES
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=FaceLES-Setup
SetupIconFile=..\..\assets\icons\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts"; Flags: checkedonce

[Files]
Source: "..\..\dist\FaceLES\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch FaceLES"; Flags: nowait postinstall skipifsilent
