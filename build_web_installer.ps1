param(
    [switch]$UseExistingDist
)

$ErrorActionPreference = 'Stop'

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building Cocktail Web App Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $repoRoot 'web\frontend'
$backendDir = Join-Path $repoRoot 'web\backend'
$backendEntry = Join-Path $backendDir 'run_backend.py'
$backendRequirements = Join-Path $backendDir 'requirements.txt'
$backendDistDir = Join-Path $backendDir 'dist'
$backendExePath = Join-Path $backendDistDir 'CocktailWebBackend.exe'
$installerScript = Join-Path $repoRoot 'web_installer_script.iss'
$distIndex = Join-Path $frontendDir 'dist\index.html'
$frontendDistDir = Join-Path $frontendDir 'dist'

function Resolve-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @('py', '-3')
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @('python')
    }
    throw "Python 3 was not found. Install Python 3 and retry."
}

function Test-FrontendBundleIsCurrent {
    param(
        [string]$FrontendDistDir
    )

    $legacyMarkers = @('Phase 1', '127.0.0.1:8001')
    foreach ($marker in $legacyMarkers) {
        $match = Select-String -Path (Join-Path $FrontendDistDir 'assets\*.js') -Pattern $marker -SimpleMatch -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($match) {
            throw "Frontend dist appears stale (found legacy marker '$marker'). Build frontend with npm and retry."
        }
    }
}

function Invoke-PythonCommand {
    param(
        [string[]]$Arguments
    )

    $launcher = Resolve-PythonLauncher
    if ($launcher.Count -gt 1) {
        & $launcher[0] $launcher[1] @Arguments
    } else {
        & $launcher[0] @Arguments
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Arguments -join ' ')"
    }
}

if (-not (Test-Path $installerScript)) {
    throw "Installer script not found: $installerScript"
}

Write-Host "[1/4] Building frontend bundle..." -ForegroundColor Yellow
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Push-Location $frontendDir
    npm install
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "npm install failed"
    }

    npm run build
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "npm run build failed"
    }
    Pop-Location
    Write-Host "Frontend build completed." -ForegroundColor Green
} elseif (Test-Path $distIndex) {
    if ($UseExistingDist) {
        Write-Host "npm not found. Reusing existing frontend build at web/frontend/dist because -UseExistingDist was specified." -ForegroundColor Yellow
    } else {
        throw "npm not found. Refusing to reuse existing frontend build by default to avoid stale UI packaging. Install Node.js/npm, or re-run with -UseExistingDist if you intentionally want to reuse current dist output."
    }
} else {
    throw "npm not found and no existing frontend build detected at $distIndex. Install Node.js (npm) and retry."
}

if (-not (Test-Path $distIndex)) {
    throw "Frontend build output missing: $distIndex"
}

Test-FrontendBundleIsCurrent -FrontendDistDir $frontendDistDir
Write-Host ""

Write-Host "[2/4] Building backend executable..." -ForegroundColor Yellow
if (-not (Test-Path $backendEntry)) {
    throw "Backend entry script not found: $backendEntry"
}
if (-not (Test-Path $backendRequirements)) {
    throw "Backend requirements file not found: $backendRequirements"
}

Invoke-PythonCommand -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-PythonCommand -Arguments @('-m', 'pip', 'install', '-r', $backendRequirements)
Invoke-PythonCommand -Arguments @('-m', 'pip', 'install', 'pyinstaller')

if (Test-Path $backendDistDir) {
    Remove-Item -Path $backendDistDir -Recurse -Force
}

Push-Location $backendDir
try {
    Invoke-PythonCommand -Arguments @(
        '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--onefile',
        '--name', 'CocktailWebBackend',
        '--distpath', 'dist',
        '--workpath', 'build',
        '--specpath', '.',
        '--paths', '.',
        'run_backend.py'
    )
}
finally {
    Pop-Location
}

if (-not (Test-Path $backendExePath)) {
    throw "Backend executable build output missing: $backendExePath"
}
Write-Host "Backend executable built: $backendExePath" -ForegroundColor Green
Write-Host ""

Write-Host "[3/4] Checking Inno Setup compiler..." -ForegroundColor Yellow
$isccPath = (Get-Command iscc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
if (-not $isccPath) {
    $candidates = @(
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 5\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $isccPath = $candidate
            break
        }
    }
}

if (-not $isccPath) {
    throw "Inno Setup compiler (iscc) not found. Install Inno Setup and retry."
}
Write-Host "Inno Setup found: $isccPath" -ForegroundColor Green
Write-Host ""

Write-Host "[4/4] Building installer..." -ForegroundColor Yellow
Push-Location $repoRoot
& $isccPath $installerScript
$innoExit = $LASTEXITCODE
Pop-Location

if ($innoExit -ne 0) {
    throw "Inno Setup build failed"
}

Write-Host "" 
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Build Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installer: Output\CocktailDatabaseWebInstaller.exe" -ForegroundColor Green
