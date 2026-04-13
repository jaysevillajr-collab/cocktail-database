# PowerShell script to build the Cocktail Database installer

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building Cocktail Database Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Install dependencies
Write-Host "[1/3] Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "Dependencies installed successfully." -ForegroundColor Green
Write-Host ""

# Step 2: Build executable with PyInstaller
Write-Host "[2/3] Building executable with PyInstaller..." -ForegroundColor Yellow
pyinstaller --clean cocktail_database.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to build executable" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "Executable built successfully." -ForegroundColor Green
Write-Host ""

# Step 3: Build installer with Inno Setup
Write-Host "[3/3] Building installer with Inno Setup..." -ForegroundColor Yellow

# Check if Inno Setup is installed
$innoSetupPath = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $innoSetupPath) {
    # Try common installation paths
    $commonPaths = @(
        "${env:ProgramFiles}\Inno Setup 6\iscc.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\iscc.exe",
        "${env:ProgramFiles}\Inno Setup 5\iscc.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\iscc.exe"
    )
    
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            $innoSetupPath = $path
            break
        }
    }
}

if (-not $innoSetupPath) {
    Write-Host "WARNING: Inno Setup (iscc) not found." -ForegroundColor Yellow
    Write-Host "Please install Inno Setup from https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host "Or run the installer script manually:" -ForegroundColor Yellow
    Write-Host "  iscc installer_script.iss" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The executable has been built in the dist\ folder." -ForegroundColor Green
    Read-Host "Press Enter to exit"
    exit 1
}

& $innoSetupPath installer_script.iss
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to build installer" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "Installer built successfully." -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Build Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installer location: Output\CocktailDatabaseInstaller.exe" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
