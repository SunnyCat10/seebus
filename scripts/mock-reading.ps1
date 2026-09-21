param(
    [Parameter(Mandatory = $true)]
    [string]$StationId,

    [Parameter(Mandatory = $true)]
    [ValidateRange(0.0, 1.0)]
    [double]$Occupancy
)

. "$PSScriptRoot\load-env.ps1"

if (-not $env:SEEBUS_SENSOR_TOKEN) {
    Write-Error "SEEBUS_SENSOR_TOKEN is not set."
    exit 1
}

$baseUrl = $env:SEEBUS_API_URL

if (-not $baseUrl) {
    $baseUrl = "http://localhost:8080"
}

$url = "$baseUrl/api/readings"

$body = @{
    stationId = $StationId
    occupancy = $Occupancy
    measuredAt = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json

$headers = @{
    Authorization = "Bearer $env:SEEBUS_SENSOR_TOKEN"
}

Write-Host "Sending mocked sensor reading..."
Write-Host "Station:   $StationId"
Write-Host "Occupancy: $Occupancy"
Write-Host "Endpoint:  $url"

try {
    $response = Invoke-RestMethod `
        -Uri $url `
        -Method Post `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $body

    Write-Host ""
    Write-Host "Reading accepted."

    if ($response) {
        $response | ConvertTo-Json -Depth 10
    }
}
catch {
    Write-Error "Failed to send reading."

    if ($_.Exception.Response) {
        Write-Host "HTTP status: $($_.Exception.Response.StatusCode)"
    }

    Write-Host $_.Exception.Message
    exit 1
}