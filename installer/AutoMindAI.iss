#define MyAppName "AutoMind AI"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "AutoMind AI"
#define MyAppExeName "AutoMindAI.exe"

[Setup]
AppId={{2AE1E6F2-AB4A-4DC0-A5CF-1C411B318F65}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AutoMind AI
DefaultGroupName=AutoMind AI
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=AutoMindAI-Setup
SetupIconFile=..\assets\automind.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
VersionInfoVersion=0.1.0.0
VersionInfoProductName=AutoMind AI
VersionInfoDescription=AutoMind AI Installer
VersionInfoCompany=AutoMind AI
VersionInfoCopyright=Copyright (c) 2026

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\AutoMindAI.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AutoMind AI"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AutoMind AI"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch AutoMind AI"; Flags: nowait postinstall skipifsilent

; User diagnostic history, reports and logs live outside Program Files and are preserved on uninstall.
