#define AppName "Lone Wolf Action Assistant"
#define AppVersion "3.1.9"
#define AppPublisher "Lone Wolf Action Assistant"
#define AppExeName "Lone Wolf Action Assistant.exe"
#define AppId "{{DE7CF6E7-C1E2-496B-8873-470524AB28CC}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=output
OutputBaseFilename=Lone Wolf Action Assistant Setup
SetupIconFile=..\logo.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup
VersionInfoCompany={#AppPublisher}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\Lone Wolf Action Assistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "MicrosoftEdgeWebview2Setup.exe"; Flags: dontcopy

[Dirs]
Name: "{code:GetBooksRoot}"
Name: "{code:GetBooksRoot}\lw"
Name: "{commonappdata}\{#AppName}\books"; Permissions: users-modify; Check: IsAdminInstallMode
Name: "{commonappdata}\{#AppName}\books\lw"; Permissions: users-modify; Check: IsAdminInstallMode

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Lone Wolf Action Assistant"; ValueType: string; ValueName: "BooksDir"; ValueData: "{code:GetBooksRoot}"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Lone Wolf Action Assistant"; ValueType: string; ValueName: "InstallScope"; ValueData: "{code:GetInstallScope}"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2ClientId = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

var
  BookChoicePage: TInputOptionWizardPage;
  BookZipPage: TInputFileWizardPage;
  BookFolderPage: TInputDirWizardPage;

function GetBooksRoot(Param: String): String;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{commonappdata}\{#AppName}\books')
  else
    Result := ExpandConstant('{localappdata}\{#AppName}\books');
end;

function GetInstallScope(Param: String): String;
begin
  if IsAdminInstallMode then
    Result := 'all-users'
  else
    Result := 'current-user';
end;

function HasWebView2At(RootKey: Integer; KeyName: String): Boolean;
var
  Version: String;
begin
  Result :=
    RegQueryStringValue(RootKey, KeyName, 'pv', Version) and
    (Version <> '') and (Version <> '0.0.0.0');
end;

function IsWebView2Installed: Boolean;
var
  ClientKey: String;
begin
  ClientKey := 'Software\Microsoft\EdgeUpdate\Clients\' + WebView2ClientId;
  Result :=
    HasWebView2At(HKCU, ClientKey) or
    HasWebView2At(HKLM, ClientKey) or
    HasWebView2At(HKLM32, ClientKey);
end;

procedure InstallWebView2;
var
  ResultCode: Integer;
begin
  if IsWebView2Installed then
    Exit;

  case MsgBox(
    'Microsoft Edge WebView2 Runtime is required but was not detected.' + #13#10 + #13#10 +
    'Choose Yes to install it through this setup. Choose No to stop setup so you can install it yourself.',
    mbConfirmation, MB_YESNO) of
    IDYES:
      begin
        ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
        if not Exec(
          ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'),
          '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode
        ) or (ResultCode <> 0) then
          RaiseException('WebView2 Runtime installation failed.');
        if not IsWebView2Installed then
          RaiseException('WebView2 Runtime was not detected after installation.');
      end;
    IDNO:
      RaiseException('Setup was stopped so WebView2 Runtime can be installed separately.');
  end;
end;

procedure InitializeWizard;
begin
  BookChoicePage := CreateInputOptionPage(
    wpSelectTasks,
    'Optional Project Aon Book Import',
    'Would you like to import books during setup?',
    'Book files are not included. You can skip this and import books later from inside the app.',
    False,
    False
  );
  BookChoicePage.Add('Import books during setup');
  BookChoicePage.Values[0] := False;

  BookFolderPage := CreateInputDirPage(
    BookChoicePage.ID,
    'Optional Extracted Book Import',
    'Select a folder containing extracted Project Aon books.',
    'The books are validated and copied into managed storage. Leave this blank to import books later from inside the app.',
    False,
    ''
  );
  BookFolderPage.Add('Extracted books folder:');
  BookFolderPage.Values[0] := GetBooksRoot('');

  BookZipPage := CreateInputFilePage(
    BookFolderPage.ID,
    'Optional Project Aon ZIP Import',
    'Select a downloaded Project Aon ZIP.',
    'You can import additional ZIPs later from inside the app. Leave this blank to skip ZIP import.'
  );
  BookZipPage.Add('Project Aon ZIP:', 'ZIP files|*.zip', '.zip');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result :=
    ((PageID = BookFolderPage.ID) or (PageID = BookZipPage.ID)) and
    (not BookChoicePage.Values[0]);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpReady then
    InstallWebView2;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  SourcePath: String;
begin
  if CurStep <> ssPostInstall then
    Exit;
  if not BookChoicePage.Values[0] then
    Exit;

  SourcePath := Trim(BookFolderPage.Values[0]);
  if (SourcePath <> '') and (CompareText(SourcePath, GetBooksRoot('')) <> 0) then
    if not Exec(
      ExpandConstant('{app}\{#AppExeName}'),
      '--import-books "' + SourcePath + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode
    ) or (ResultCode <> 0) then
      MsgBox(
        'The selected extracted books could not be imported. Installation will continue; use Install Books inside the app to try again.',
        mbError, MB_OK
      );

  SourcePath := Trim(BookZipPage.Values[0]);
  if SourcePath <> '' then
    if not Exec(
      ExpandConstant('{app}\{#AppExeName}'),
      '--import-books "' + SourcePath + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode
    ) or (ResultCode <> 0) then
      MsgBox(
        'The selected ZIP could not be imported. Installation will continue; use Install Books inside the app to try again.',
        mbError, MB_OK
      );
end;
