@echo off
setlocal enabledelayedexpansion
REM Provisions a repo-local, portable dev toolchain into tools\ so building this
REM project does NOT require installing Visual Studio, a system-wide Python, or
REM the Vulkan SDK. Nothing here touches system PATH, the registry, or Program
REM Files - everything lands under tools\ and is picked up by
REM workspace-env.cmd. Safe to delete tools\ and re-run any time.
REM
REM Components installed (repo-local only):
REM   tools\python       Python 3.13 (per-user install redirected into this
REM                      folder - includes tkinter and pip, no admin needed)
REM   tools\cmake        CMake (~50MB)
REM   tools\w64devkit    portable GCC + Ninja + Make toolchain (~100MB)
REM                      (this is what lets us skip installing Visual Studio -
REM                       llama.cpp builds fine with MinGW-w64 GCC)
REM   tools\VulkanSDK    Vulkan SDK, installed silently into this folder only
REM                      (needed to compile llama.cpp's Vulkan backend - headers
REM                      + glslc shader compiler; the *runtime* DLL end users
REM                      need already ships with their GPU driver)
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
REM Python 3.13, extracted (not "installed") into tools\python
REM ---------------------------------------------------------------
if exist "%TOOLS_DIR%\python\python.exe" (
    echo [python] already present, skipping.
) else (
    set "PY_VERSION=3.13.14"
    echo [python] downloading the Python !PY_VERSION! installer...
    curl -L --fail -o "%DOWNLOAD_DIR%\python-installer.exe" "https://www.python.org/ftp/python/!PY_VERSION!/python-!PY_VERSION!-amd64.exe"
    if errorlevel 1 (
        echo ERROR: failed to download the Python installer.
        exit /b 1
    )

    REM A normal /quiet InstallAllUsers=0 install silently becomes a no-op if
    REM this exact Python version+architecture is already installed for the
    REM current Windows user anywhere else (msiexec treats it as "already
    REM installed", even with a different TargetDir - confirmed by testing).
    REM Extracting the installer's constituent MSI packages and running an
    REM administrative install (msiexec /a, a pure file copy with no
    REM registration) avoids that entirely and can never conflict with any
    REM other Python install on the machine.
    echo [python] extracting installer payload...
    set "PY_LAYOUT_DIR=%DOWNLOAD_DIR%\py-layout"
    if exist "!PY_LAYOUT_DIR!" rmdir /s /q "!PY_LAYOUT_DIR!"
    "%DOWNLOAD_DIR%\python-installer.exe" /layout "!PY_LAYOUT_DIR!" /quiet
    if errorlevel 1 (
        echo ERROR: failed to extract the Python installer payload.
        exit /b 1
    )

    REM /layout skips any package Windows already has cached from a prior
    REM install of the same version - fall back to that cache for anything
    REM still missing so this also works cleanly on a machine that already
    REM has this exact Python version installed some other way. The cache
    REM folder name embeds the version (e.g. "{GUID}v3.13.14150.0"), and
    REM MUST be filtered on that - a machine with multiple cached Python
    REM versions will otherwise silently mix in a wrong-version MSI (this
    REM shipped once already: an unfiltered search grabbed a cached 3.12
    REM core.msi ahead of 3.13, producing a python.exe that couldn't start
    REM at all).
    for %%M in (core.msi exe.msi lib.msi tcltk.msi) do (
        if not exist "!PY_LAYOUT_DIR!\%%M" (
            REM dir /s doesn't support a wildcard in a middle path segment, so
            REM search broadly for %%M and filter matches by version via findstr.
            for /f "delims=" %%F in ('dir /s /b "%LocalAppData%\Package Cache\%%M" 2^>nul ^| findstr /C:"v!PY_VERSION!" 2^>nul') do (
                copy /y "%%F" "!PY_LAYOUT_DIR!\%%M" >nul
            )
        )
    )

    echo [python] extracting into %TOOLS_DIR%\python ...
    mkdir "%TOOLS_DIR%\python" 2>nul
    for %%M in (core.msi exe.msi lib.msi tcltk.msi) do (
        if not exist "!PY_LAYOUT_DIR!\%%M" (
            echo ERROR: could not find %%M after extraction or in the Windows Installer cache.
            exit /b 1
        )
        msiexec /a "!PY_LAYOUT_DIR!\%%M" TARGETDIR="%TOOLS_DIR%\python" /qn
        if errorlevel 1 (
            echo ERROR: msiexec /a failed for %%M.
            exit /b 1
        )
    )

    if not exist "%TOOLS_DIR%\python\python.exe" (
        echo ERROR: Python extraction did not produce %TOOLS_DIR%\python\python.exe
        exit /b 1
    )

    REM pip.msi's administrative install path doesn't work reliably this way
    REM (fails with a generic MSI error) - ensurepip bootstraps the same pip
    REM from a wheel bundled inside the standard library, no MSI needed.
    echo [python] bootstrapping pip...
    "%TOOLS_DIR%\python\python.exe" -m ensurepip --upgrade
    if errorlevel 1 (
        echo ERROR: ensurepip failed.
        exit /b 1
    )

    echo [python] installing app dependencies...
    "%TOOLS_DIR%\python\python.exe" -m pip install --no-warn-script-location -r "%TOOLS_DIR%\..\app\requirements.txt"
    if errorlevel 1 (
        echo ERROR: pip install failed.
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

call "%TOOLS_DIR%\workspace-env.cmd"

echo ============================================================
echo  Done. The portable toolchain lives entirely under:
echo    %TOOLS_DIR%
echo  build\build-llama.cmd and installer\build-installer.cmd will
echo  pick it up automatically - nothing else to configure.
echo ============================================================
exit /b 0
