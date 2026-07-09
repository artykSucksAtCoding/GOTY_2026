<#
Полная пересборка установщика Best Game Ever с нуля:
  1) PyInstaller собирает игру в installer/dist/BestGameEver (--onedir)
  2) Inno Setup (ISCC) упаковывает её в installer/output/BestGameEver-Setup-<версия>.exe

Запускать из корня репозитория:
    powershell -File installer/build.ps1

Требования (устанавливаются один раз):
    python -m pip install pyinstaller
    winget install -e --id JRSoftware.InnoSetup
#>

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    Write-Host "== Шаг 1/2: PyInstaller ==" -ForegroundColor Cyan
    python -m PyInstaller installer/game.spec --noconfirm --distpath installer/dist --workpath installer/build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller завершился с ошибкой (код $LASTEXITCODE)" }

    Write-Host "== Шаг 2/2: Inno Setup ==" -ForegroundColor Cyan
    $isccCmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LocalAppData}\Programs\Inno Setup 6\ISCC.exe"
    )
    if ($isccCmd) {
        $iscc = $isccCmd.Source
    } else {
        $iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
        if (-not $iscc) {
            throw "ISCC.exe не найден. Установите Inno Setup: winget install -e --id JRSoftware.InnoSetup"
        }
    }
    & $iscc "installer\installer.iss"
    if ($LASTEXITCODE -ne 0) { throw "ISCC завершился с ошибкой (код $LASTEXITCODE)" }

    Write-Host "Готово! Установщик лежит в installer\output\" -ForegroundColor Green
}
finally {
    Pop-Location
}
