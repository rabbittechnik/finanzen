#Requires -Version 5.1
<#
.SYNOPSIS
  Legt eine Verknüpfung auf dem Windows-Desktop an, die start_desktop.bat ausführt.
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
$shortcut.Description = 'Finanzen / Dokumenten-Organizer (lokal, App-Fenster)'
$shortcut.Save()

Write-Host "Verknüpfung angelegt: $lnkPath"
