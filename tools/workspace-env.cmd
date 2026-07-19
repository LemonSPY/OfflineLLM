@echo off
REM Shared helper: puts the repo-local portable toolchain (if present) at the front
REM of PATH for the current cmd session, so build-llama.cmd / build-installer.cmd
REM work the same whether or not anything is installed system-wide.
REM
REM Not meant to be run directly - call this at the top of other scripts:
REM   call "%~dp0..\tools\workspace-env.cmd"

set "TOOLS_DIR=%~dp0"
if "%TOOLS_DIR:~-1%"=="\" set "TOOLS_DIR=%TOOLS_DIR:~0,-1%"

if exist "%TOOLS_DIR%\dotnet\dotnet.exe" (
    set "DOTNET_ROOT=%TOOLS_DIR%\dotnet"
    set "PATH=%TOOLS_DIR%\dotnet;%PATH%"
)

if exist "%TOOLS_DIR%\dotnet\tools\wix.exe" (
    set "PATH=%TOOLS_DIR%\dotnet\tools;%PATH%"
)

if exist "%TOOLS_DIR%\cmake\bin\cmake.exe" (
    set "PATH=%TOOLS_DIR%\cmake\bin;%PATH%"
)

if exist "%TOOLS_DIR%\w64devkit\bin\gcc.exe" (
    set "PATH=%TOOLS_DIR%\w64devkit\bin;%PATH%"
)

if exist "%TOOLS_DIR%\VulkanSDK" (
    for /d %%D in ("%TOOLS_DIR%\VulkanSDK\*") do set "VULKAN_SDK=%%D"
    if defined VULKAN_SDK set "PATH=%VULKAN_SDK%\Bin;%PATH%"
)

exit /b 0
