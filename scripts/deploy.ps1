param(
    [string]$HostName
)

. "$PSScriptRoot\load-env.ps1"

if (-not $HostName) {
    $HostName = $env:SEEBUS_DEPLOY_HOST
}

if (-not $HostName) {
    Write-Error "SEEBUS_DEPLOY_HOST is not set."
    exit 1
}

$keyPath = "$HOME\.ssh\gerbil"

Write-Host "Deploying SeeBus to $HostName..."

ssh `
    -i $keyPath `
    "opc@$HostName" `
    "cd ~/seebus && ./deploy/deploy.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Deployment failed."
    exit 1
}

Write-Host "Deployment complete."