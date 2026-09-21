$repoRoot = Resolve-Path "$PSScriptRoot\.."

$exampleFile = Join-Path $repoRoot ".env.example"
$envFile = Join-Path $repoRoot ".env"

if (Test-Path $envFile) {
    Write-Host ".env already exists. Nothing to do."
    exit 0
}

Copy-Item $exampleFile $envFile

Write-Host ""
Write-Host "Created .env from .env.example."
Write-Host ""
Write-Host "Edit .env and replace the placeholder values before running SeeBus."