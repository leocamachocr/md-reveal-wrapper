# install_shortcut.ps1
# Creates a Start Menu shortcut for md-reveal-wrapper and pins it to the Taskbar.

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbsPath    = Join-Path $projectDir "run_app.vbs"
$icoPath    = Join-Path $projectDir "assets\app.ico"
$shortcutName = "md-reveal-wrapper"

# --- 1. Create shortcut in Start Menu (required for pinning) ----------------
$startMenuDir = [System.IO.Path]::Combine(
    [Environment]::GetFolderPath("StartMenu"), "Programs"
)
$lnkPath = Join-Path $startMenuDir "$shortcutName.lnk"

$wsh  = New-Object -ComObject WScript.Shell
$link = $wsh.CreateShortcut($lnkPath)
$link.TargetPath      = "wscript.exe"
$link.Arguments       = "`"$vbsPath`""
$link.WorkingDirectory = $projectDir
$link.Description     = "md-reveal-wrapper — Markdown to Reveal.js"
if (Test-Path $icoPath) { $link.IconLocation = $icoPath }
$link.Save()

Write-Host "Shortcut created: $lnkPath"

# --- 2. Pin to Taskbar via Shell verb ----------------------------------------
$shell  = New-Object -ComObject Shell.Application
$folder = $shell.Namespace((Split-Path $lnkPath))
$item   = $folder.ParseName((Split-Path $lnkPath -Leaf))
$verb   = $item.Verbs() | Where-Object { $_.Name -match "Pin to taskbar" }

if ($verb) {
    $verb.DoIt()
    Write-Host "Pinned to Taskbar."
} else {
    Write-Host ""
    Write-Host "Auto-pin not available on this Windows version."
    Write-Host "Manual step: right-click the Start Menu shortcut and choose 'Pin to taskbar'."
    Write-Host "Start Menu path: $lnkPath"
}

Write-Host ""
Write-Host "Done."
