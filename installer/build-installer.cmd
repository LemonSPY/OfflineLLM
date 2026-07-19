@echo off
setlocal enabledelayedexpansion
REM Publishes OfflineLlm.App self-contained and packages it into an MSI with WiX v4.
REM
REM PREREQUISITES
REM   - .NET 8 SDK
REM   - WiX Toolset v4 CLI: dotnet tool install --global wix
REM   - build\build-llama.cmd already run, so the app's publish output picks up
REM     engine\llama-server.exe (see AppPaths.LlamaServerExePath)
REM
REM OUTPUT
REM   installer\bin\OfflineLlm-Setup.msi
REM
REM USAGE
REM   build-installer.cmd [Release|Debug]

set "CONFIGURATION=%~1"
if "%CONFIGURATION%"=="" set "CONFIGURATION=Release"

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "APP_PROJECT=%REPO_ROOT%\src\OfflineLlm.App\OfflineLlm.App.csproj"
set "PUBLISH_DIR=%SCRIPT_DIR%publish"
set "ICON_PATH=%REPO_ROOT%\src\OfflineLlm.App\Assets\app.ico"
set "OUT_DIR=%SCRIPT_DIR%bin"

if not exist "%ICON_PATH%" (
    echo ERROR: Missing %ICON_PATH% - add a real app icon first ^(see src\OfflineLlm.App\Assets\README.md^).
    exit /b 1
)

echo Publishing OfflineLlm.App ^(%CONFIGURATION%, self-contained win-x64^)...
dotnet publish "%APP_PROJECT%" -c %CONFIGURATION% -r win-x64 --self-contained true -p:WindowsPackageType=None -o "%PUBLISH_DIR%"
if errorlevel 1 (
    echo ERROR: dotnet publish failed.
    exit /b 1
)

echo Building MSI with WiX v4...
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

wix build "%SCRIPT_DIR%Product.wxs" -d "AppPublishDir=%PUBLISH_DIR%" -d "AppIcon=%ICON_PATH%" -arch x64 -out "%OUT_DIR%\OfflineLlm-Setup.msi"
if errorlevel 1 (
    echo ERROR: wix build failed.
    exit /b 1
)

echo Done: %OUT_DIR%\OfflineLlm-Setup.msi
exit /b 0
