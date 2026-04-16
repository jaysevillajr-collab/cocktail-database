$ErrorActionPreference = 'Stop'

$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installRoot = Split-Path -Parent $appRoot
$backendDir = Join-Path $appRoot 'backend'
$backendExe = Join-Path $backendDir 'CocktailWebBackend.exe'
$userRoot = Join-Path $env:LOCALAPPDATA 'CocktailDatabaseWeb'
$userDataDir = Join-Path $userRoot 'data'
$pidFilePath = Join-Path $userRoot 'backend.pid'
$installedDbPath = Join-Path $installRoot 'cocktail_database.db'
$installedImagesPath = Join-Path $installRoot 'images'
$userDbPath = Join-Path $userDataDir 'cocktail_database.db'
$userImagesPath = Join-Path $userDataDir 'images'
$apiUrl = 'http://127.0.0.1:8002'
$healthUrl = "$apiUrl/health"
$backendArgs = '--host 127.0.0.1 --port 8002'

function Test-BackendRunning {
    if (Test-Path $pidFilePath) {
        $rawPid = (Get-Content $pidFilePath -Raw).Trim()
        if ($rawPid) {
            try {
                $pidValue = [int]$rawPid
                $proc = Get-Process -Id $pidValue -ErrorAction Stop
                if ($proc) {
                    return $true
                }
            } catch {
            }
        }
    }

    $processName = [System.IO.Path]::GetFileNameWithoutExtension($backendExe)
    $runningBackend = Get-Process -Name $processName -ErrorAction SilentlyContinue
    return ($null -ne $runningBackend)
}

if (-not (Test-Path $backendDir)) {
    throw "Backend directory not found: $backendDir"
}

if (-not (Test-Path $backendExe)) {
    throw "Backend executable not found: $backendExe"
}

if (-not (Test-Path $userRoot)) {
    New-Item -Path $userRoot -ItemType Directory | Out-Null
}

if (-not (Test-Path $userDataDir)) {
    New-Item -Path $userDataDir -ItemType Directory | Out-Null
}

if (-not (Test-Path $userDbPath) -and (Test-Path $installedDbPath)) {
    Write-Host 'Preparing user database...'
    Copy-Item -Path $installedDbPath -Destination $userDbPath -Force
}

if (-not (Test-Path $userImagesPath) -and (Test-Path $installedImagesPath)) {
    Write-Host 'Preparing user image library...'
    Copy-Item -Path $installedImagesPath -Destination $userImagesPath -Recurse -Force
}

$env:COCKTAIL_DB_PATH = $userDbPath
$env:COCKTAIL_IMAGES_PATH = $userImagesPath

if (-not (Test-BackendRunning)) {
    Write-Host 'Starting backend service...'
    $backendProcess = Start-Process -FilePath $backendExe -ArgumentList $backendArgs -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru
    Set-Content -Path $pidFilePath -Value $backendProcess.Id -Encoding UTF8
}

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Warning 'Backend is still starting. The browser will open anyway.'
}

Start-Process "$apiUrl/"
Write-Host 'Cocktail Web App launched.'
