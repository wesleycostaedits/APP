; Instalador do Animador (Inno Setup). Gerado pelo GitHub Actions.
; Uso: iscc /DVersao=2.0.0 instalador\Animador.iss

#ifndef Versao
  #define Versao "2.0.0"
#endif

[Setup]
AppId={{6F3C2B8E-5A41-4C7B-9E0D-3A7F1C2D9B64}
AppName=Animador
AppVersion={#Versao}
AppPublisher=Wesley Costa Edits
DefaultDirName={localappdata}\Programs\Animador
DefaultGroupName=Animador
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Animador-Instalador-{#Versao}
SetupIconFile=..\recursos\icone.ico
UninstallDisplayIcon={app}\Animador.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "..\dist\Animador.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Animador.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Animador"; Filename: "{app}\Animador.exe"
Name: "{group}\Desinstalar Animador"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Animador"; Filename: "{app}\Animador.exe"; Tasks: atalho

[Run]
Filename: "{app}\Animador.exe"; Description: "Abrir o Animador"; Flags: nowait postinstall skipifsilent
