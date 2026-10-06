#define VersionFile FileOpen(AddBackslash(SourcePath) + "version.txt")
#define AppVersion Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)

[Setup]
AppId={{B60D44C5-A5EF-4CE8-9ED4-1BEBB7252B13}
AppName=Anycubic Uploader
AppVersion={#AppVersion}
AppPublisher=nzrbits
AppSupportURL=https://github.com/nzrbits/anycubic-uploader
DefaultDirName={localappdata}\Programs\AnycubicUploader
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=AnycubicUploader-Setup
SetupIconFile=anycubic.ico
UninstallDisplayIcon={app}\AnycubicUploader.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=no
DisableFinishedPage=yes
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\AnycubicUploader.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Anycubic Uploader"; Filename: "{app}\AnycubicUploader.exe"

[Run]
Filename: "{app}\AnycubicUploader.exe"; Flags: nowait skipifsilent

[Code]
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo,
  MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result := 'Install Anycubic Uploader for your Windows account.';
end;
