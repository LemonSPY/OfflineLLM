@echo off
setlocal enabledelayedexpansion
REM Publishes OfflineLlm.App self-contained and packages it into an MSI with WiX v4.
REM
REM PREREQUISITES (pick one)
REM   A) run tools\setup-workspace.cmd once (recommended - installs a local .NET 8
REM      SDK and the WiX v4 CLI under tools\, no system-wide install needed)
REM   B) have the .NET 8 SDK and `dotnet tool install --global wix` done yourself
REM
REM   Either way: build\build-llama.cmd must have been run first, so the app's
REM   publish output picks up engine\llama-server.exe (see AppPaths.LlamaServerExePath)
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

call "%REPO_ROOT%\tools\workspace-env.cmd"

if not exist "%ICON_PATH%" (
    echo ERROR: Missing %ICON_PATH% - add a real app icon first ^(see src\OfflineLlm.App\Assets\README.md^).
    exit /b 1
)

echo Publishing OfflineLlm.App ^(%CONFIGURATION%, self-contained win-x64^)...
dotnet publish "%APP_PROJECT%" -c %CONFIGURATION% -r win-x64 --self-contained true -p:Platform=x64 -p:WindowsPackageType=None -o "%PUBLISH_DIR%"
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
