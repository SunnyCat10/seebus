. "$PSScriptRoot\load-env.ps1"

$repoRoot = Resolve-Path "$PSScriptRoot\.."
$backendDir = Join-Path $repoRoot "backend"

Set-Location $backendDir

Write-Host "Starting SeeBus backend..."

if ($env:OS -eq "Windows_NT") {
    .\mvnw.cmd spring-boot:run
}
else {
    ./mvnw spring-boot:run
}