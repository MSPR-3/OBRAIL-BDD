#Requires -Version 5.1
param(
    [string]$SqlSource = "init_obrail_db.sql"
)

$ErrorActionPreference = "Stop"

# 1. Verify source SQL file exists
if (-not (Test-Path $SqlSource)) {
    Write-Error "Fichier SQL introuvable : $SqlSource"
    exit 1
}

# 2. Create ./db/ directory if needed
$dbDir = Join-Path $PSScriptRoot "db"
if (-not (Test-Path $dbDir)) {
    New-Item -ItemType Directory -Path $dbDir | Out-Null
    Write-Host "Dossier cree : $dbDir"
}

# 3. Read SQL file and strip last line if it starts with \unrestrict
$lines = Get-Content -Path $SqlSource -Encoding UTF8

$lastLine = $lines[-1].TrimStart()
if ($lastLine -match '^\\.?unrestrict') {
    Write-Host "Suppression de la derniere ligne pgAdmin : '$($lines[-1])'"
    $lines = $lines[0..($lines.Length - 2)]
}

# 4. Write cleaned file to ./db/
$dest = Join-Path $dbDir "init_obrail_db.sql"
$lines | Set-Content -Path $dest -Encoding UTF8
Write-Host "Fichier nettoye copie vers : $dest"

# 5. Launch docker compose
Write-Host "`nDemarrage de Docker Compose..."
docker compose up --build -d

if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose a echoue (code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Write-Host "`nConteneur demarre. Attendez que la base soit prete..."
Write-Host "Pour suivre les logs : docker compose logs -f db"
Write-Host "Pour tester la connexion : docker exec -it obrail_db psql -U obrail_user -d obrail"
