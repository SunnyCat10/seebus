param(
    [string]$EnvFile,

    [switch]$PreserveExisting
)

$repoRoot = Resolve-Path "$PSScriptRoot\.."

# Preserve old behavior:
# no -EnvFile means use the repository .env file.
if (-not $EnvFile) {
    $EnvFile = Join-Path $repoRoot ".env"
}

if (-not (Test-Path $EnvFile)) {
    Write-Error "Environment file not found: $EnvFile"
    exit 1
}

Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()

    # Ignore blank lines and comments
    if (-not $line -or $line.StartsWith("#")) {
        return
    }

    $parts = $line -split "=", 2

    if ($parts.Count -ne 2) {
        Write-Warning "Ignoring invalid environment line: $line"
        return
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim()

    if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        Write-Warning "Ignoring invalid environment variable name: $name"
        return
    }

    # Allow optional quoted values
    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    # By default, match the old behavior and overwrite the
    # process environment variable.
    if (-not $PreserveExisting -or -not (Test-Path "Env:$name")) {
        [Environment]::SetEnvironmentVariable(
            $name,
            $value,
            "Process"
        )
    }
}