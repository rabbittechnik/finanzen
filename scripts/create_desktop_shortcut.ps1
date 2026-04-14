#Requires -Version 5.1
<#
.SYNOPSIS
  Legt eine Verknüpfung auf dem Windows-Desktop an, die start_desktop.bat ausführt.

.NOTES
  Das Werkstatt-Programm unter
  C:\Users\Bianc\Documents\rabbit technik reperatur
  nutzt eine PWA (manifest.json, display=standalone). Streamlit bietet das nicht nativ;
  start_desktop.ps1 öffnet stattdessen Edge/Chrome mit --app= (eigenes Fenster, vergleichbar).
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptsDir = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $scriptsDir '..')).Path
$batPath = Join-Path $scriptsDir 'start_desktop.bat'
if (-not (Test-Path -LiteralPath $batPath)) {
    Write-Error "Nicht gefunden: $batPath"
    exit 1
}

$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop 'Finanzen.lnk'

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($lnkPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $projectRoot
$shortcut.WindowStyle = 1
$shortcut.Description = 'Finanzen / Dokumenten-Organizer (lokal, App-Fenster wie PWA standalone)'

$iconCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe')
)
$iconExe = $iconCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($iconExe) {
    $shortcut.IconLocation = "$iconExe,0"
}

$shortcut.Save()

Write-Host "Verknüpfung angelegt: $lnkPath"
