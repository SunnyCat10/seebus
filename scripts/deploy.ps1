$hostName = $env:SEEBUS_DEPLOY_HOST

if (-not $hostName) {
    Write-Error "SEEBUS_DEPLOY_HOST is not set."
    exit 1
}

Write-Host "Deploying Seebus..."

ssh "opc@$hostName" `
    "cd ~/seebus && ./deploy/deploy.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Deployment failed."
    exit 1
}

Write-Host "Deployment complete."