$swaggerUrl = "http://localhost:8080/swagger-ui.html"
$healthUrl = "http://localhost:8080/api/health"

try {
    Invoke-WebRequest `
        -Uri $healthUrl `
        -TimeoutSec 2 `
        -ErrorAction Stop | Out-Null

    Write-Host "SeeBus backend is running."
    Write-Host "Opening Swagger UI..."

    Start-Process $swaggerUrl
}
catch {
    Write-Error "SeeBus backend does not appear to be running."
    Write-Host "Start it with:"
    Write-Host "  .\scripts\dev.ps1"
}