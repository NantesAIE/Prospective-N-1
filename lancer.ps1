# Lance l'application en local : back-end FastAPI + front Vite, puis ouvre le navigateur.
# Usage : .\lancer.ps1            (ou double-clic sur lancer.cmd)
#         .\lancer.ps1 -Demo      (mode démo, sans passerelle ni réseau)
#         .\lancer.ps1 -SansNavigateur
# Ctrl+C arrête les deux serveurs.

param(
    [switch]$Demo,
    [switch]$SansNavigateur
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$UrlBack = 'http://127.0.0.1:8000/api/sante'
$UrlFront = 'http://127.0.0.1:5173'

function Etape([string]$texte) { Write-Host "==> $texte" -ForegroundColor Cyan }

function Attendre-Url([string]$url, [int]$secondes = 90) {
    $limite = (Get-Date).AddSeconds($secondes)
    while ((Get-Date) -lt $limite) {
        try {
            Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return $true
        } catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

function Arreter-Arbre($processus) {
    if ($processus -and -not $processus.HasExited) {
        taskkill /T /F /PID $processus.Id 2>$null | Out-Null
    }
}

# Prérequis
foreach ($outil in 'uv', 'npm') {
    if (-not (Get-Command $outil -ErrorAction SilentlyContinue)) {
        Write-Host "Outil manquant : $outil. Installez-le puis relancez." -ForegroundColor Red
        exit 1
    }
}
foreach ($port in 8000, 5173) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "Le port $port est déjà utilisé. Fermez l'instance en cours puis relancez." -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path '.env')) {
    Etape 'Création de .env depuis .env.example (renseignez AGENT_API_KEY)'
    Copy-Item '.env.example' '.env'
}

Etape 'Dépendances Python (uv sync)'
uv sync --project backend --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path 'frontend\node_modules')) {
    Etape 'Dépendances front (npm install)'
    npm install --prefix frontend --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Demo) {
    $env:DEMO = 'true'
    Etape 'Mode démo actif'
}

$back = $null
$front = $null
try {
    Etape 'Démarrage du back-end (http://127.0.0.1:8000)'
    $back = Start-Process -FilePath 'uv' -ArgumentList 'run', '--project', 'backend', 'serveur' `
        -NoNewWindow -PassThru

    Etape "Démarrage du front ($UrlFront)"
    $front = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' `
        -WorkingDirectory 'frontend' -NoNewWindow -PassThru

    if (-not (Attendre-Url $UrlBack)) { throw 'Le back-end ne répond pas.' }
    if (-not (Attendre-Url $UrlFront)) { throw 'Le front ne répond pas.' }

    Write-Host ''
    Write-Host "Application prête : $UrlFront   (Ctrl+C pour arrêter)" -ForegroundColor Green
    Write-Host ''
    if (-not $SansNavigateur) { Start-Process $UrlFront }

    while (-not $back.HasExited -and -not $front.HasExited) { Start-Sleep -Seconds 1 }
    Write-Host 'Un des serveurs s''est arrêté.' -ForegroundColor Yellow
} catch {
    Write-Host "Erreur : $_" -ForegroundColor Red
} finally {
    Etape 'Arrêt des serveurs'
    Arreter-Arbre $front
    Arreter-Arbre $back
}
