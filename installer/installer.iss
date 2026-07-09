; Inno Setup скрипт для Best Game Ever.
; Собирает готовый каталог PyInstaller (installer/dist/BestGameEver, см.
; installer/game.spec) в один setup.exe с ярлыками в меню "Пуск", на рабочем
; столе (по желанию) и полноценным удалением через "Программы и компоненты".
;
; Порядок сборки установщика с нуля (из корня репозитория):
;   1) python -m PyInstaller installer/game.spec --noconfirm ^
;        --distpath installer/dist --workpath installer/build
;   2) ISCC installer/installer.iss
; (см. также installer/build.ps1 — делает оба шага одной командой)
;
; Результат появится в installer/output/BestGameEver-Setup-<версия>.exe

#define MyAppName "Best Game Ever"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Best Game Ever"
#define MyAppExeName "BestGameEver.exe"
#define MyDistDir "dist\BestGameEver"

[Setup]
AppId={{7F0B7B5C-6E6E-4E9C-9B2E-2E7C7C6B6A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; По умолчанию — Program Files; сама игра пишет пользовательские данные
; (рекорды) в %APPDATA%\BestGameEver, а не рядом с .exe, поэтому установка в
; защищённую системную папку не мешает сохранению прогресса (см. leaderboard.py).
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=BestGameEver-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Весь каталог, собранный PyInstaller (--onedir): BestGameEver.exe + _internal
; со всеми ресурсами (images/sound/model.joblib) и Python-зависимостями.
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Рекорды/лидерборд в %APPDATA%\BestGameEver — сознательно НЕ удаляются
; стандартным деинсталлятором, чтобы не терять прогресс игрока при
; переустановке/обновлении игры. Если понадобится полностью стереть
; пользовательские данные — сделать это отдельно вручную.
