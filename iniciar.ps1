# Arranca Sentinel en la red local para usarla desde el celular o la PC.
# Uso:  .\iniciar.ps1                      (HTTP, puerto 5000)
#       .\iniciar.ps1 -Https                (HTTPS: activa la cámara en el celular)
#       .\iniciar.ps1 -ConDatos             (carga los usuarios de demostración)
#       .\iniciar.ps1 -Puerto 8080 -Https
param(
    [int]$Puerto = 5000,
    [switch]$Https,
    [switch]$ConDatos
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "No se encontró 'uv'. Instálalo desde https://docs.astral.sh/uv/" -ForegroundColor Red
    exit 1
}

Write-Host "Instalando dependencias..." -ForegroundColor Cyan
uv sync

$env:PORT = "$Puerto"

$argumentos = @("run", "python", "servidor.py")
if ($Https) { $argumentos += "--https" }
if ($ConDatos) { $argumentos += "--con-datos" }

& uv @argumentos