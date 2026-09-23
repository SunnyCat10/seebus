param(
    [Parameter(Mandatory = $true)]
    [string]$StationId,

    [Parameter(Mandatory = $true)]
    [ValidateRange(0.0, 1.0)]
    [double]$Occupancy,

    [switch]$Dev
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path

# ----------------------------------------------------------------------
# Environment
# ----------------------------------------------------------------------

if ($Dev) {
    $envFile = Join-Path $repoRoot ".env.example"

    . "$PSScriptRoot\load-env.ps1" -EnvFile $envFile

    $environmentName = "development (.env.example)"
}
else {
    # Preserve the existing behavior:
    # load-env.ps1 defaults to the repository .env file.
    . "$PSScriptRoot\load-env.ps1"

    $environmentName = ".env"
}

if (-not $env:SEEBUS_SENSOR_TOKEN) {
    Write-Error "SEEBUS_SENSOR_TOKEN is not set."
    exit 1
}

$baseUrl = $env:SEEBUS_API_URL

if (-not $baseUrl) {
    $baseUrl = "http://localhost:8080"
}

$baseUrl = $baseUrl.TrimEnd("/")
$url = "$baseUrl/api/readings"

# ----------------------------------------------------------------------
# Request
# ----------------------------------------------------------------------

$body = @{
    stationId  = $StationId
    occupancy  = $Occupancy
    measuredAt = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json

$headers = @{
    Authorization = "Bearer $env:SEEBUS_SENSOR_TOKEN"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "  SeeBus Mock Sensor Reading" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host ""

Write-Host "  Environment   " -NoNewline -ForegroundColor DarkGray
Write-Host $environmentName -ForegroundColor White

Write-Host "  Station       " -NoNewline -ForegroundColor DarkGray
Write-Host $StationId -ForegroundColor White

Write-Host "  Occupancy     " -NoNewline -ForegroundColor DarkGray
Write-Host $Occupancy -ForegroundColor White

Write-Host "  Endpoint      " -NoNewline -ForegroundColor DarkGray
Write-Host $url -ForegroundColor Green

Write-Host ""

try {
    $response = Invoke-RestMethod `
        -Uri $url `
        -Method Post `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $body

    Write-Host "  Reading accepted." -ForegroundColor Green
    Write-Host ""

    if ($response) {
        $response | ConvertTo-Json -Depth 10
    }
}
catch {
    Write-Host "  Failed to send reading." -ForegroundColor Red
    Write-Host ""

    if ($_.Exception.Response) {
        Write-Host "  HTTP status: " -NoNewline -ForegroundColor DarkGray
        Write-Host $_.Exception.Response.StatusCode -ForegroundColor Red
    }

    if ($_.ErrorDetails.Message) {
        Write-Host ""
        Write-Host "  Response body:" -ForegroundColor DarkGray
        Write-Host $_.ErrorDetails.Message
    }

    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red

    exit 1
}