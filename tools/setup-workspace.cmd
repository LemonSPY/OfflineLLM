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
    REM Current releases ship as a self-extracting 7z .exe (older releases were
    REM plain .zip files - if this 404s, check
    REM https://github.com/skeeto/w64devkit/releases/latest for the current asset name).
    curl -L --fail -o "%DOWNLOAD_DIR%\w64devkit.7z.exe" "https://github.com/skeeto/w64devkit/releases/download/v2.8.0/w64devkit-x64-2.8.0.7z.exe"
    if errorlevel 1 (
        echo ERROR: failed to download w64devkit.
        exit /b 1
    )
    echo [w64devkit] extracting...
    if exist "%DOWNLOAD_DIR%\w64devkit-extract" rmdir /s /q "%DOWNLOAD_DIR%\w64devkit-extract"
    "%DOWNLOAD_DIR%\w64devkit.7z.exe" -y -o"%DOWNLOAD_DIR%\w64devkit-extract" >nul
    if errorlevel 1 (
        echo ERROR: failed to extract w64devkit.
        exit /b 1
    )
    if exist "%DOWNLOAD_DIR%\w64devkit-extract\bin\gcc.exe" (
        move /y "%DOWNLOAD_DIR%\w64devkit-extract" "%TOOLS_DIR%\w64devkit" >nul
    ) else if exist "%DOWNLOAD_DIR%\w64devkit-extract\w64devkit\bin\gcc.exe" (
        move /y "%DOWNLOAD_DIR%\w64devkit-extract\w64devkit" "%TOOLS_DIR%\w64devkit" >nul
    ) else (
        echo ERROR: extracted w64devkit but could not find bin\gcc.exe in the expected location.
        exit /b 1
    )
)

REM ---------------------------------------------------------------
REM Vulkan SDK - installed silently, contained to tools\VulkanSDK
REM ---------------------------------------------------------------
REM The official installer's "SDK Core" component unconditionally requires
REM administrator rights for one of its install actions, even with --root
REM pointed at a non-system folder - there's no CLI switch to skip it (verified
REM against its --help output and by trying --nf/--no-force-installations).
REM Everything else in this script runs unelevated; only this one step asks
REM Windows to elevate, which means a UAC prompt appears once and needs a
REM human to click "Yes" - it cannot be scripted around.
if exist "%TOOLS_DIR%\VulkanSDK\Include\vulkan\vulkan.h" (
    echo [vulkan] already present, skipping.
) else (
    echo [vulkan] downloading Vulkan SDK installer...
    curl -L --fail -o "%DOWNLOAD_DIR%\vulkan-sdk.exe" "https://sdk.lunarg.com/sdk/download/latest/windows/vulkan-sdk.exe"
    if errorlevel 1 (
        echo ERROR: failed to download the Vulkan SDK installer.
        exit /b 1
    )

    net session >nul 2>&1
    if errorlevel 1 (
        echo [vulkan] this step requires one-time administrator approval - a UAC
        echo          prompt will appear now. Please click "Yes".
        powershell -NoProfile -NonInteractive -Command ^
            "Start-Process -FilePath '%DOWNLOAD_DIR%\vulkan-sdk.exe' -ArgumentList '--root','%TOOLS_DIR%\VulkanSDK','--accept-licenses','--default-answer','--confirm-command','install' -Verb RunAs -Wait"
    ) else (
        echo [vulkan] installing silently into %TOOLS_DIR%\VulkanSDK ...
        "%DOWNLOAD_DIR%\vulkan-sdk.exe" --root "%TOOLS_DIR%\VulkanSDK" --accept-licenses --default-answer --confirm-command install
    )

    if not exist "%TOOLS_DIR%\VulkanSDK\Include\vulkan\vulkan.h" (
        echo ERROR: Vulkan SDK install did not produce Include\vulkan\vulkan.h - it
        echo        may have failed or been cancelled at the UAC prompt.
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
