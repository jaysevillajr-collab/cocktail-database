@echo off
echo ========================================
echo Building Cocktail Database Installer
echo ========================================
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully.
echo.

echo [2/3] Building executable with PyInstaller...
pyinstaller --clean cocktail_database.spec
if %errorlevel% neq 0 (
    echo ERROR: Failed to build executable
    pause
    exit /b 1
)
echo Executable built successfully.
echo.

echo [3/3] Building installer with Inno Setup...
REM Check if Inno Setup is installed
where iscc >nul 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Inno Setup (iscc) not found in PATH.
    echo Please install Inno Setup from https://jrsoftware.org/isdl.php
    echo Or run the installer script manually:
    echo   iscc installer_script.iss
    echo.
    echo The executable has been built in the dist\ folder.
    pause
    exit /b 1
)

iscc installer_script.iss
if %errorlevel% neq 0 (
    echo ERROR: Failed to build installer
    pause
    exit /b 1
)
echo Installer built successfully.
echo.

echo ========================================
echo Build Complete!
echo ========================================
echo Installer location: Output\CocktailDatabaseInstaller.exe
echo.
pause
