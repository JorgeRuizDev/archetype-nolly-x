<#
.SYNOPSIS
    Instalador y sincronizador de 1 solo comando para Archetype Nolly X Tone Suite.
.DESCRIPTION
    Clona o actualiza el paquete de herramientas Python, AGENTS.md, catálogo YAML
    y presets de usuario directamente en C:\ProgramData\Neural DSP\Archetype Nolly X.
    Configura el entorno virtual con uv/python y valida el funcionamiento de nolly.cmd.
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
Write-Host "  🎸 Archetype Nolly X Tone Suite - Setup & Restorer        " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Repositorio: $RepoUrl" -ForegroundColor Gray
Write-Host "Destino:     $InstallDir" -ForegroundColor Gray
Write-Host ""

# 1. Comprobar Git
Write-Host "[1/5] Comprobando dependencias del sistema..." -ForegroundColor Yellow
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git no está instalado o no está en el PATH. Instálalo con: winget install --id Git.Git"
    exit 1
}

# 2. Configurar safe.directory para evitar error de 'dubious ownership' en ProgramData
$gitSafePath = $InstallDir -replace '\\', '/'
git config --global --add safe.directory $gitSafePath 2>$null
git config --global --add safe.directory $InstallDir 2>$null

# 3. Preparar directorio y clonar/sincronizar repositorio
Write-Host "[2/5] Descargando y sincronizando repositorio..." -ForegroundColor Yellow

$parentDir = Split-Path $InstallDir -Parent
if (-not (Test-Path $parentDir)) {
    New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
}

if (-not (Test-Path $InstallDir)) {
    # Caso A: El directorio no existe, clonar limpiamente
    git clone --branch $Branch $RepoUrl $InstallDir
    Set-Location $InstallDir
} elseif (Test-Path (Join-Path $InstallDir ".git")) {
    # Caso B: Ya es un repositorio Git, actualizar
    Set-Location $InstallDir
    git fetch origin $Branch
    git checkout -f $Branch
    git pull origin $Branch
} else {
    # Caso C: Directorio pre-existente tras reinstalar Nolly (con presets de fábrica)
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

# 4. Configurar dependencias de Python (uv o venv nativo)
Write-Host "[3/5] Configurando entorno de Python y dependencias..." -ForegroundColor Yellow

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "  -> 'uv' detectado. Sincronizando entorno virtual..." -ForegroundColor Green
    uv sync
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "  -> 'uv' no detectado, usando Python estándar..." -ForegroundColor Gray
    if (-not (Test-Path (Join-Path $InstallDir ".venv"))) {
        python -m venv (Join-Path $InstallDir ".venv")
    }
    $venvPy = Join-Path $InstallDir ".venv\Scripts\python.exe"
    & $venvPy -m pip install -e .
} else {
    Write-Warning "No se encontró ni 'uv' ni 'python'. Se recomienda instalar uv: irm https://astral.sh/uv/install.ps1 | iex"
}

# 5. Validar AGENTS.md y herramientas CLI
Write-Host "[4/5] Verificando archivos clave..." -ForegroundColor Yellow
$agentsFile = Join-Path $InstallDir "AGENTS.md"
$nollyCmd = Join-Path $InstallDir "nolly.cmd"

if (Test-Path $agentsFile) {
    Write-Host "  [OK] AGENTS.md presente y listo para asistentes IA." -ForegroundColor Green
} else {
    Write-Warning "AGENTS.md no se encontró en la raíz."
}

if (Test-Path $nollyCmd) {
    Write-Host "  [OK] CLI nolly.cmd listo." -ForegroundColor Green
} else {
    Write-Warning "nolly.cmd no se encontró en la raíz."
}

# 6. Test de humo
Write-Host "[5/5] Ejecutando prueba de funcionamiento..." -ForegroundColor Yellow
try {
    & $nollyCmd search "metal" --limit 1 | Out-Null
    Write-Host "  [OK] Búsqueda de presets validada con éxito." -ForegroundColor Green
} catch {
    Write-Warning "La prueba de ejecución de nolly.cmd no finalizó correctamente. Verifica las dependencias."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  🎉 ¡Instalación y restauración completada con éxito!      " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Para empezar a usar el CLI:" -ForegroundColor Cyan
Write-Host "  cd `"$InstallDir`"" -ForegroundColor White
Write-Host "  .\nolly.cmd search `"metal`"" -ForegroundColor White
Write-Host "  .\nolly.cmd create --base `"All-Purpose Metal Rhythm`" --song `"Tool - Lateralus`" --num `"00`" --name `"Drop D Riff`"" -ForegroundColor White
Write-Host ""
