# Build the React member portal into core/static/frontend for Django to serve.
$ErrorActionPreference = "Stop"
$frontend = (Resolve-Path (Join-Path $PSScriptRoot "..\front-end")).Path
Write-Host "Building React app from $frontend ..."
Push-Location $frontend
try {
  if (-not (Test-Path "node_modules")) {
    npm ci
  }
  npm run build:django
  Write-Host "Done. Output: mcs/core/static/frontend (served at /static/frontend/)"
}
finally {
  Pop-Location
}
