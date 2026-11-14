<#
.SYNOPSIS
    1-command installer and restorer for the Archetype Nolly X Tone Suite.
.DESCRIPTION
    Clones or updates the Python toolsuite, AGENTS.md, YAML catalog,
    and user presets directly into C:\ProgramData\Neural DSP\Archetype Nolly X.
    Configures the virtual environment with uv/python and validates nolly.cmd.
.EXAMPLE
    irm https://raw.githubusercontent.com/JorgeRuizDev/archetype-nolly-x/main/install.ps1 | iex
#>

[CmdletBinding()]
param (
    [string]$RepoUrl = "https://github.com/JorgeRuizDev/archetype-nolly-x.git",
    [string]$Branch = "main",
    [string]$InstallDir = "$env:ProgramData\Neural DSP\Archetype Nolly X"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Archetype Nolly X Tone Suite - Setup & Restorer           " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Repository: $RepoUrl" -ForegroundColor Gray
Write-Host "Target:     $InstallDir" -ForegroundColor Gray
Write-Host ""

# 1. Check Git
Write-Host "[1/5] Checking system dependencies..." -ForegroundColor Yellow
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed or not in PATH. Install it via: winget install --id Git.Git"
    exit 1
}

# 2. Configure safe.directory to prevent dubious ownership issues in ProgramData
$gitSafePath = $InstallDir -replace '\\', '/'
git config --global --add safe.directory $gitSafePath 2>$null
git config --global --add safe.directory $InstallDir 2>$null

# 3. Prepare target directory and clone / sync repository
Write-Host "[2/5] Downloading and synchronizing repository..." -ForegroundColor Yellow

$parentDir = Split-Path $InstallDir -Parent
if (-not (Test-Path $parentDir)) {
    New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
}

if (-not (Test-Path $InstallDir)) {
    # Case A: Directory does not exist, clean clone
    git clone --branch $Branch $RepoUrl $InstallDir
    Set-Location $InstallDir
} elseif (Test-Path (Join-Path $InstallDir ".git")) {
    # Case B: Already a Git repository, update
    Set-Location $InstallDir
    git fetch origin $Branch
    git checkout -f $Branch
    git pull origin $Branch
} else {
    # Case C: Pre-existing directory after reinstalling Nolly (contains factory presets)
    Set-Location $InstallDir
    git init -b $Branch
    git config --global --add safe.directory $gitSafePath 2>$null
    git remote add origin $RepoUrl 2>$null
    if ($LASTEXITCODE -ne 0) {
        git remote set-url origin $RepoUrl
    }
    git fetch origin $Branch
    git checkout -f $Branch
}

# 4. Configure Python environment & dependencies (uv or standard venv)
Write-Host "[3/5] Setting up Python environment and dependencies..." -ForegroundColor Yellow

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "  -> 'uv' detected. Synchronizing virtual environment..." -ForegroundColor Green
    uv sync
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "  -> 'uv' not found, using standard Python..." -ForegroundColor Gray
    if (-not (Test-Path (Join-Path $InstallDir ".venv"))) {
        python -m venv (Join-Path $InstallDir ".venv")
    }
    $venvPy = Join-Path $InstallDir ".venv\Scripts\python.exe"
    & $venvPy -m pip install -e .
} else {
    Write-Warning "Neither 'uv' nor 'python' was found. It is recommended to install uv: irm https://astral.sh/uv/install.ps1 | iex"
}

# 5. Validate key files
Write-Host "[4/5] Verifying core files..." -ForegroundColor Yellow
$agentsFile = Join-Path $InstallDir "AGENTS.md"
$nollyCmd = Join-Path $InstallDir "nolly.cmd"

if (Test-Path $agentsFile) {
    Write-Host "  [OK] AGENTS.md present and ready for AI assistants." -ForegroundColor Green
} else {
    Write-Warning "AGENTS.md was not found in root directory."
}

if (Test-Path $nollyCmd) {
    Write-Host "  [OK] nolly.cmd CLI ready." -ForegroundColor Green
} else {
    Write-Warning "nolly.cmd was not found in root directory."
}

# 6. Smoke test
Write-Host "[5/5] Running verification smoke test..." -ForegroundColor Yellow
try {
    & $nollyCmd search "metal" --limit 1 | Out-Null
    Write-Host "  [OK] Preset search test passed successfully." -ForegroundColor Green
} catch {
    Write-Warning "nolly.cmd smoke test encountered an issue. Please verify dependencies."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Setup & restore completed successfully!                   " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "To start using the CLI:" -ForegroundColor Cyan
Write-Host "  cd `"$InstallDir`"" -ForegroundColor White
Write-Host "  .\nolly.cmd search `"metal`"" -ForegroundColor White
Write-Host "  .\nolly.cmd create --base `"All-Purpose Metal Rhythm`" --song `"Tool - Lateralus`" --num `"00`" --name `"Drop D Riff`"" -ForegroundColor White
Write-Host ""
