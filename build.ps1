[CmdletBinding()]
param(
    [switch]$SkipInstaller,
    [switch]$SkipWebView2Download
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$PackagedExe = Join-Path $ProjectRoot 'dist\Lone Wolf Action Assistant\Lone Wolf Action Assistant.exe'
$PackagedCliExe = Join-Path $ProjectRoot 'dist\Lone Wolf Action Assistant\Lone Wolf Action Assistant CLI.exe'
$LegacyOneFileExe = Join-Path $ProjectRoot 'dist\Lone Wolf Action Assistant.exe'
$CliBuildRoot = Join-Path $ProjectRoot 'build\LoneWolf_ActionAssistant_CLI'
$CliSpecRoot = Join-Path $CliBuildRoot 'spec'
$CliDataSource = Join-Path $ProjectRoot 'data'
$IconSource = Join-Path $ProjectRoot 'logo.ico'
$CliVersionInfo = Join-Path $ProjectRoot 'version_info_cli.txt'
$InstallerRoot = Join-Path $ProjectRoot 'installer'
$Bootstrapper = Join-Path $InstallerRoot 'MicrosoftEdgeWebview2Setup.exe'
$IsccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
)

Push-Location $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
            throw 'uv is required to create the pinned Python 3.13 build environment.'
        }
        uv python install 3.13
        uv venv '.venv' --python 3.13
    }
    $Python = $VenvPython

    uv pip install --python $Python -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

    magick 'lone-wolf icon.png' -background '#11110f' -gravity center -extent 1536x1536 `
        -define icon:auto-resize=256,128,64,48,32,24,16 'logo.ico'
    if ($LASTEXITCODE -ne 0) { throw 'Icon conversion failed.' }

    & $Python -m PyInstaller --noconfirm --clean 'LoneWolf_ActionAssistant.spec'
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

    # The desktop executable is intentionally windowed. Build a small,
    # console-subsystem worker for the embedded WinPTY terminal instead of
    # making the desktop process create a visible Windows Terminal tab.
    New-Item -ItemType Directory -Path $CliSpecRoot -Force | Out-Null
    & $Python -m PyInstaller --noconfirm --clean --onefile --console `
        --name 'Lone Wolf Action Assistant CLI' `
        --distpath (Split-Path -Parent $PackagedCliExe) `
        --workpath $CliBuildRoot `
        --specpath $CliSpecRoot `
        --add-data "$CliDataSource;data" `
        --icon $IconSource `
        --version-file $CliVersionInfo `
        'saa_cli.py'
    if ($LASTEXITCODE -ne 0) { throw 'Embedded CLI worker build failed.' }
    if (-not (Test-Path -LiteralPath $PackagedCliExe)) { throw 'Embedded CLI worker was not created.' }

    & $PackagedExe --self-test
    if ($LASTEXITCODE -ne 0) { throw 'Frozen executable self-test failed.' }
    if (Test-Path -LiteralPath $LegacyOneFileExe) {
        Write-Warning "An obsolete single-file build remains at '$LegacyOneFileExe'. Use '$PackagedExe' for the current fast-launch build."
    }

    if ($SkipInstaller) { return }

    if (-not $SkipWebView2Download -and -not (Test-Path -LiteralPath $Bootstrapper)) {
        New-Item -ItemType Directory -Path $InstallerRoot -Force | Out-Null
        Invoke-WebRequest `
            -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' `
            -OutFile $Bootstrapper
    }
    if (-not (Test-Path -LiteralPath $Bootstrapper)) {
        throw 'The WebView2 Evergreen Bootstrapper is missing. Download it or omit -SkipWebView2Download.'
    }

    $Iscc = $IsccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $Iscc) {
        throw 'Inno Setup 6 was not found. Install it, then run build.ps1 again.'
    }
    & $Iscc (Join-Path $InstallerRoot 'LoneWolf_ActionAssistant.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
}
finally {
    Pop-Location
}
