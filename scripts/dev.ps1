param(
    [switch]$UseEnv
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path

$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"

$exampleEnvFile = Join-Path $repoRoot ".env.example"
$localEnvFile = Join-Path $repoRoot ".env"

# ----------------------------------------------------------------------
# Environment
# ----------------------------------------------------------------------

# Standard development configuration.
. "$PSScriptRoot\load-env.ps1" -EnvFile $exampleEnvFile

$envDescription = ".env.example"

# Optionally override values with .env.
if ($UseEnv) {
    if (-not (Test-Path $localEnvFile)) {
        Write-Error ".env not found."
        exit 1
    }

    . "$PSScriptRoot\load-env.ps1" -EnvFile $localEnvFile

    $envDescription = ".env.example + .env overrides"
}

# ----------------------------------------------------------------------
# Process management
# ----------------------------------------------------------------------

function Stop-ProcessTree {
    param(
        [System.Diagnostics.Process]$Process
    )

    if (-not $Process) {
        return
    }

    try {
        if ($Process.HasExited) {
            return
        }

        Write-Host "Stopping process tree $($Process.Id)..."

        if ($env:OS -eq "Windows_NT") {
            taskkill /PID $Process.Id /T /F 2>$null | Out-Null
        }
        else {
            Stop-Process `
                -Id $Process.Id `
                -Force `
                -ErrorAction SilentlyContinue
        }
    }
    catch {
        # Process may already have exited.
    }
}

# ----------------------------------------------------------------------
# Start development environment
# ----------------------------------------------------------------------

$apiUrl = $env:SEEBUS_API_URL.TrimEnd("/")
$frontendUrl = "http://localhost:5173"
$swaggerUrl = "$apiUrl/swagger-ui.html"

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "  SeeBus Development Environment" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host ""

Write-Host "  Environment   " -NoNewline -ForegroundColor DarkGray
Write-Host $envDescription -ForegroundColor White

Write-Host "  Backend       " -NoNewline -ForegroundColor DarkGray
Write-Host $apiUrl -ForegroundColor Green

Write-Host "  Frontend      " -NoNewline -ForegroundColor DarkGray
Write-Host $frontendUrl -ForegroundColor Green

if ($env:SEEBUS_SWAGGER_ENABLED -eq "true") {
    Write-Host "  Swagger UI    " -NoNewline -ForegroundColor DarkGray
    Write-Host $swaggerUrl -ForegroundColor Cyan
}
else {
    Write-Host "  Swagger UI    " -NoNewline -ForegroundColor DarkGray
    Write-Host "disabled" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Admin token   " -NoNewline -ForegroundColor DarkGray
Write-Host $env:SEEBUS_ADMIN_TOKEN -ForegroundColor Yellow

Write-Host "  Sensor token  " -NoNewline -ForegroundColor DarkGray
Write-Host $env:SEEBUS_SENSOR_TOKEN -ForegroundColor Yellow

Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Press Ctrl+C to stop SeeBus" -ForegroundColor DarkGray
Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

$backendProcess = $null
$frontendProcess = $null

try {
    if ($env:OS -eq "Windows_NT") {
        $backendProcess = Start-Process `
            -FilePath (Join-Path $backendDir "mvnw.cmd") `
            -ArgumentList "spring-boot:run" `
            -WorkingDirectory $backendDir `
            -NoNewWindow `
            -PassThru

        $frontendProcess = Start-Process `
            -FilePath "npm.cmd" `
            -ArgumentList "run", "dev" `
            -WorkingDirectory $frontendDir `
            -NoNewWindow `
            -PassThru
    }
    else {
        $backendProcess = Start-Process `
            -FilePath (Join-Path $backendDir "mvnw") `
            -ArgumentList "spring-boot:run" `
            -WorkingDirectory $backendDir `
            -NoNewWindow `
            -PassThru

        $frontendProcess = Start-Process `
            -FilePath "npm" `
            -ArgumentList "run", "dev" `
            -WorkingDirectory $frontendDir `
            -NoNewWindow `
            -PassThru
    }

    while (
        -not $backendProcess.HasExited -and
        -not $frontendProcess.HasExited
    ) {
        Start-Sleep -Milliseconds 500
    }

    if ($backendProcess.HasExited) {
        Write-Warning "Backend exited with code $($backendProcess.ExitCode)."
    }

    if ($frontendProcess.HasExited) {
        Write-Warning "Frontend exited with code $($frontendProcess.ExitCode)."
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping SeeBus development environment..."

    Stop-ProcessTree $frontendProcess
    Stop-ProcessTree $backendProcess

    Write-Host "SeeBus stopped."
}