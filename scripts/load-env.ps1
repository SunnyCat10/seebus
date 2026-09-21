$repoRoot = Resolve-Path "$PSScriptRoot\.."
$envFile = Join-Path $repoRoot ".env"

if (-not (Test-Path $envFile)) {
    Write-Error ".env not found. Run scripts/setup.ps1 first."
    exit 1
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()

    # Ignore blank lines and comments
    if (-not $line -or $line.StartsWith("#")) {
        return
    }

    $parts = $line -split "=", 2

    if ($parts.Count -ne 2) {
        Write-Warning "Ignoring invalid .env line: $line"
        return
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim()

    # Allow optional quoted values
    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    [Environment]::SetEnvironmentVariable(
        $name,
        $value,
        "Process"
    )
}