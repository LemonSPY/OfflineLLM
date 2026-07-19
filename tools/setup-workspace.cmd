@echo off
setlocal enabledelayedexpansion
REM Provisions a repo-local, portable dev toolchain into tools\ so building this
REM project does NOT require installing Visual Studio, a system-wide .NET SDK,
REM CMake, or the Vulkan SDK. Nothing here touches system PATH, the registry, or
REM Program Files - everything lands under tools\ and is picked up by
REM workspace-env.cmd. Safe to delete tools\ and re-run any time.
REM
REM Components installed (repo-local only):
REM   tools\dotnet       .NET 8 SDK (xcopy install, ~200MB)
REM   tools\cmake        CMake (~50MB)
REM   tools\w64devkit    portable GCC + Ninja + Make toolchain (~100MB)
REM                      (this is what lets us skip installing Visual Studio -
REM                       llama.cpp builds fine with MinGW-w64 GCC)
REM   tools\VulkanSDK    Vulkan SDK, installed silently into this folder only
REM                      (needed to compile llama.cpp's Vulkan backend - headers
REM                      + glslc shader compiler; the *runtime* DLL end users
REM                      need already ships with their GPU driver)
REM   tools\dotnet\tools\wix.exe   WiX v4 CLI (local dotnet tool install)
REM
REM USAGE
REM   tools\setup-workspace.cmd
REM
REM This downloads several hundred MB to ~1.5GB total. Run it once per machine;
REM re-run is a no-op for anything already present.

set "TOOLS_DIR=%~dp0"
if "%TOOLS_DIR:~-1%"=="\" set "TOOLS_DIR=%TOOLS_DIR:~0,-1%"
set "DOWNLOAD_DIR=%TOOLS_DIR%\_downloads"

if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%"

echo ============================================================
echo  OfflineLLM workspace setup
echo  Installing portable tools into: %TOOLS_DIR%
echo  (nothing is installed system-wide)
echo ============================================================

REM ---------------------------------------------------------------
REM .NET 8 SDK (xcopy-deployable zip)
REM ---------------------------------------------------------------
if exist "%TOOLS_DIR%\dotnet\dotnet.exe" (
    echo [dotnet] already present, skipping.
) else (
    echo [dotnet] downloading .NET 8 SDK...
    curl -L --fail -o "%DOWNLOAD_DIR%\dotnet-sdk-win-x64.zip" "https://aka.ms/dotnet/8.0/dotnet-sdk-win-x64.zip"
    if errorlevel 1 (
        echo ERROR: failed to download .NET SDK.
        exit /b 1
    )
    echo [dotnet] extracting...
    mkdir "%TOOLS_DIR%\dotnet" 2>nul
    tar -xf "%DOWNLOAD_DIR%\dotnet-sdk-win-x64.zip" -C "%TOOLS_DIR%\dotnet"
    if errorlevel 1 (
        echo ERROR: failed to extract .NET SDK.
        exit /b 1
    )
)

REM ---------------------------------------------------------------
REM CMake (portable zip)
REM ---------------------------------------------------------------
if exist "%TOOLS_DIR%\cmake\bin\cmake.exe" (
    echo [cmake] already present, skipping.
) else (
    echo [cmake] downloading CMake...
    curl -L --fail -o "%DOWNLOAD_DIR%\cmake.zip" "https://github.com/Kitware/CMake/releases/download/v3.30.0/cmake-3.30.0-windows-x86_64.zip"
    if errorlevel 1 (
        echo ERROR: failed to download CMake.
        exit /b 1
    )
    echo [cmake] extracting...
    tar -xf "%DOWNLOAD_DIR%\cmake.zip" -C "%DOWNLOAD_DIR%"
    move /y "%DOWNLOAD_DIR%\cmake-3.30.0-windows-x86_64" "%TOOLS_DIR%\cmake" >nul
    if errorlevel 1 (
        echo ERROR: failed to extract CMake.
        exit /b 1
    )
)

REM ---------------------------------------------------------------
REM w64devkit (portable GCC + Ninja + Make) - replaces Visual Studio
REM ---------------------------------------------------------------
if exist "%TOOLS_DIR%\w64devkit\bin\gcc.exe" (
    echo [w64devkit] already present, skipping.
) else (
    echo [w64devkit] downloading portable GCC toolchain...
    curl -L --fail -o "%DOWNLOAD_DIR%\w64devkit.zip" "https://github.com/skeeto/w64devkit/releases/download/v2.0.0/w64devkit-2.0.0.zip"
    if errorlevel 1 (
        echo ERROR: failed to download w64devkit.
        exit /b 1
    )
    echo [w64devkit] extracting...
    tar -xf "%DOWNLOAD_DIR%\w64devkit.zip" -C "%DOWNLOAD_DIR%"
    move /y "%DOWNLOAD_DIR%\w64devkit" "%TOOLS_DIR%\w64devkit" >nul
    if errorlevel 1 (
        echo ERROR: failed to extract w64devkit.
        exit /b 1
    )
)

REM ---------------------------------------------------------------
REM Vulkan SDK - installed silently, contained to tools\VulkanSDK
REM ---------------------------------------------------------------
if exist "%TOOLS_DIR%\VulkanSDK" (
    echo [vulkan] already present, skipping.
) else (
    echo [vulkan] downloading Vulkan SDK installer...
    curl -L --fail -o "%DOWNLOAD_DIR%\vulkan-sdk.exe" "https://sdk.lunarg.com/sdk/download/latest/windows/vulkan-sdk.exe"
    if errorlevel 1 (
        echo ERROR: failed to download the Vulkan SDK installer.
        exit /b 1
    )
    echo [vulkan] installing silently into %TOOLS_DIR%\VulkanSDK ...
    "%DOWNLOAD_DIR%\vulkan-sdk.exe" --root "%TOOLS_DIR%\VulkanSDK" --accept-licenses --default-answer --confirm-command install
    if errorlevel 1 (
        echo ERROR: Vulkan SDK install failed.
        exit /b 1
    )
)

REM ---------------------------------------------------------------
REM WiX v4 CLI - local dotnet tool, not a global install
REM ---------------------------------------------------------------
call "%TOOLS_DIR%\workspace-env.cmd"
if exist "%TOOLS_DIR%\dotnet\tools\wix.exe" (
    echo [wix] already present, skipping.
) else (
    echo [wix] installing WiX v4 CLI as a local tool...
    dotnet tool install --tool-path "%TOOLS_DIR%\dotnet\tools" wix
    if errorlevel 1 (
        echo ERROR: failed to install WiX CLI.
        exit /b 1
    )
)

echo ============================================================
echo  Done. The portable toolchain lives entirely under:
echo    %TOOLS_DIR%
echo  build\build-llama.cmd and installer\build-installer.cmd will
echo  pick it up automatically - nothing else to configure.
echo ============================================================
exit /b 0
