$ErrorActionPreference = 'Stop'

$userRoot = Join-Path $env:LOCALAPPDATA 'CocktailDatabaseWeb'
$pidFilePath = Join-Path $userRoot 'backend.pid'
$stoppedAny = $false

if (Test-Path $pidFilePath) {
    $rawPid = (Get-Content $pidFilePath -Raw).Trim()
    if ($rawPid) {
        try {
            $pidValue = [int]$rawPid
            Stop-Process -Id $pidValue -Force -ErrorAction Stop
            Write-Host "Stopped backend process $pidValue."
            $stoppedAny = $true
        } catch {
        }
    }

    Remove-Item -Path $pidFilePath -Force -ErrorAction SilentlyContinue
}

$fallback = Get-Process -Name 'CocktailWebBackend' -ErrorAction SilentlyContinue
if ($fallback) {
    foreach ($proc in $fallback) {
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
            Write-Host "Stopped backend process $($proc.Id)."
            $stoppedAny = $true
        } catch {
            Write-Warning "Failed to stop process $($proc.Id): $($_.Exception.Message)"
        }
    }
}

if (-not $stoppedAny) {
    Write-Host 'Cocktail Web backend is not running.'
}
