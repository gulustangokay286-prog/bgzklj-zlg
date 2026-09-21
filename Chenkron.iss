; Chenkron.iss — Windows kurulum paketi (Inno Setup 6)
;
; Bu betik PyInstaller'ın ÜRETTİĞİ klasörü paketler, kaynak koddan bir şey
; derlemez. Sıra şudur:
;
;   1) python tools\build_scheduler.py      -> C++ motoru (.exe)
;   2) pyinstaller Chenkron.spec --noconfirm -> dist\Chenkron\
;   3) ISCC.exe Chenkron.iss                -> Output\ChenkronKurulum-x.y.z.exe
;
; Sürüm numarası tek yerden gelsin diye komut satırından geçirilebilir:
;   ISCC.exe /DAppVersion=5.3.8 Chenkron.iss
; Geçilmezse aşağıdaki varsayılan kullanılır ve version.py ile elle eşitlenir.

#ifndef AppVersion
  #define AppVersion "5.3.8"
#endif

#define AppName       "Chenkron"
#define AppPublisher  "Chenkron"
#define AppExeName    "Chenkron.exe"
#define SourceDir     "dist\Chenkron"

[Setup]
AppId={{8B4F2C91-5E6D-4A77-9C3B-CH3NKR0N2026}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Yönetici hakkı istemez: kullanıcı kendi profiline de kurabilsin.
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename=ChenkronKurulum-{#AppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
; Program açıkken kurulum yapılırsa dosyalar kilitli kalır; Inno önce
; kapanmasını ister.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller çıktısının TAMAMI: Chenkron.exe, _internal klasörü, OR-Tools
; DLL'leri, PySide6 ve C++ planlama motoru (scheduler\native\*.exe) dahil.
; recursesubdirs olmadan alt klasörler atlanır ve program DLL bulamaz.
Source: "{#SourceDir}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Program klasöründe çalışma sırasında oluşan artıklar; kullanıcının
; ~\.chenki_akademi altındaki ÇİZELGELERİNE dokunulmaz.
Type: filesandordirs; Name: "{app}\_internal\__pycache__"
