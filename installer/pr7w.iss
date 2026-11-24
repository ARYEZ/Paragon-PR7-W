; Paragon PR7-W installer (Inno Setup 6).
;   iscc /DAppVersion=0.1.0 installer\pr7w.iss      (after pyinstaller pr7w.spec has made dist\PR7-W)
;
; Per-user (no admin rights) into %LOCALAPPDATA%\Programs\PR7-W, Start menu entry, and (ticked)
; "Edit with PR7-W" on Explorer's right-click menu and PR7-W under "Open with" for text files.
; Registration is done by PR7-W itself (pr7w/shell.py); the uninstaller removes it again.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; AppId is permanent: it's how a new version finds and upgrades the installed one. Never change it.
AppId={{D8F51204-6E9E-4CB7-BF2E-58F4908B7937}
AppName=Paragon PR7-W
AppVersion={#AppVersion}
AppVerName=Paragon PR7-W {#AppVersion}
AppPublisher=Paragon
VersionInfoVersion={#AppVersion}
PrivilegesRequired=lowest
DefaultDirName={autopf}\PR7-W
DefaultGroupName=Paragon PR7-W
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=PR7-W-Setup-{#AppVersion}
SetupIconFile=..\pr7w\icons\app.ico
UninstallDisplayIcon={app}\PR7-W.exe
UninstallDisplayName=Paragon PR7-W
WizardStyle=modern
WizardImageFile=wizard-large-1x.bmp,wizard-large-2x.bmp
WizardSmallImageFile=wizard-small-1x.bmp,wizard-small-2x.bmp
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "contextmenu"; Description: "Add ""Edit with PR7-W"" to Explorer's right-click menu"
Name: "openwith"; Description: "List PR7-W under ""Open with"" for text and source files"
Name: "replacenotepad"; Description: "Replace Windows Notepad with PR7-W (asks for administrator permission)"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\PR7-W\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\Paragon PR7-W"; Filename: "{app}\PR7-W.exe"; Comment: "Text editor"
Name: "{autodesktop}\Paragon PR7-W"; Filename: "{app}\PR7-W.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PR7-W.exe"; Parameters: "--register-menu"; Tasks: contextmenu; Flags: runhidden waituntilterminated; StatusMsg: "Adding ""Edit with PR7-W""..."
Filename: "{app}\PR7-W.exe"; Parameters: "--unregister-menu"; Tasks: not contextmenu; Flags: runhidden waituntilterminated
Filename: "{app}\PR7-W.exe"; Parameters: "--register-open-with"; Tasks: openwith; Flags: runhidden waituntilterminated
Filename: "{app}\PR7-W.exe"; Parameters: "--unregister-open-with"; Tasks: not openwith; Flags: runhidden waituntilterminated
; Replacing Notepad is machine-wide (notepad.exe's redirect in HKLM): run elevated, one UAC prompt.
Filename: "{app}\PR7-W.exe"; Parameters: "--replace-notepad"; Tasks: replacenotepad; Verb: "runas"; Flags: shellexec runhidden waituntilterminated; StatusMsg: "Replacing Windows Notepad..."
Filename: "{app}\PR7-W.exe"; Description: "{cm:LaunchProgram,Paragon PR7-W}"; Flags: nowait postinstall skipifsilent
; Updates (Check for Updates runs this installer with /SILENT /relaunch=1): start PR7-W again when done.
Filename: "{app}\PR7-W.exe"; Flags: nowait runasoriginaluser; Check: Relaunch

[UninstallRun]
Filename: "{app}\PR7-W.exe"; Parameters: "--unregister"; Flags: runhidden waituntilterminated; RunOnceId: "PR7WUnregister"
; Recorded only when "Replace Windows Notepad" was chosen, so others get no admin prompt on uninstall.
Filename: "{app}\PR7-W.exe"; Parameters: "--restore-notepad"; Tasks: replacenotepad; Verb: "runas"; Flags: shellexec runhidden waituntilterminated; RunOnceId: "PR7WRestoreNotepad"

[Code]
// True only when the updater asked for it (/relaunch=1): normal and CI installs behave as before.
function Relaunch: Boolean;
begin
  Result := ExpandConstant('{param:relaunch|0}') = '1';
end;
