#Requires -Version 5.1
<#
.SYNOPSIS
  Startet die Streamlit-App lokal und öffnet sie im Browser-App-Fenster (Edge/Chrome --app=),
  damit sie wie ein eigenständiges Desktop-Programm wirkt.

.NOTES
  Vorbereitung im Projektroot: python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
  Desktop-Verknüpfung: scripts\create_desktop_shortcut.ps1 einmal ausführen.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $ProjectRoot

$port = if ($env:STREAMLIT_SERVER_PORT) { $env:STREAMLIT_SERVER_PORT.Trim() } else { '8501' }
$baseUrl = "http://127.0.0.1:$port/"

$activate = Join-Path $ProjectRoot '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $activate) {
    . $activate
} else {
    Write-Warning 'Kein .venv gefunden — es wird Streamlit aus dem PATH verwendet. Empfohlen: venv anlegen und pip install -r requirements.txt'
}

$st = Get-Command streamlit -ErrorAction SilentlyContinue
if (-not $st) {
    $stExe = Join-Path $ProjectRoot '.venv\Scripts\streamlit.exe'
    if (Test-Path -LiteralPath $stExe) {
        $env:PATH = (Join-Path $ProjectRoot '.venv\Scripts') + ';' + $env:PATH
    }
}
if (-not (Get-Command streamlit -ErrorAction SilentlyContinue)) {
    Write-Error 'streamlit wurde nicht gefunden. Bitte virtuelle Umgebung anlegen und Abhängigkeiten installieren.'
    exit 1
}

$openApp = {
    param([string]$Url)
    foreach ($i in 1..90) {
        try {
            $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
        (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe')
    )
    $exe = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($exe) {
        Start-Process -FilePath $exe -ArgumentList "--app=$Url"
    } else {
        Start-Process $Url
    }
}

$job = Start-Job -ScriptBlock $openApp -ArgumentList $baseUrl

try {
    & streamlit run app.py `
        --server.headless true `
        --browser.gatherUsageStats false `
        --server.address 127.0.0.1 `
        --server.port $port
} finally {
    Stop-Job -Job $job -ErrorAction SilentlyContinue
    Remove-Job -Job $job -ErrorAction SilentlyContinue
}
