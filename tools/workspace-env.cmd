@echo off
REM Shared helper: puts the repo-local portable toolchain (if present) at the front
REM of PATH for the current cmd session, so build-llama.cmd / build-installer.cmd
REM work the same whether or not anything is installed system-wide.
REM
REM Not meant to be run directly - call this at the top of other scripts:
REM   call "%~dp0..\tools\workspace-env.cmd"

set "TOOLS_DIR=%~dp0"
if "%TOOLS_DIR:~-1%"=="\" set "TOOLS_DIR=%TOOLS_DIR:~0,-1%"

if exist "%TOOLS_DIR%\python\python.exe" (
    set "PATH=%TOOLS_DIR%\python;%TOOLS_DIR%\python\Scripts;%PATH%"
)

if exist "%TOOLS_DIR%\cmake\bin\cmake.exe" (
    set "PATH=%TOOLS_DIR%\cmake\bin;%PATH%"
)

if exist "%TOOLS_DIR%\w64devkit\bin\gcc.exe" (
    set "PATH=%TOOLS_DIR%\w64devkit\bin;%PATH%"
)

REM Our install used --root pointed straight at tools\VulkanSDK, so files land
REM flat there (Include\, Lib\, Bin\) rather than nested under a version folder
REM the way a system-wide install nests under e.g. C:\VulkanSDK\1.4.x.x\.
if exist "%TOOLS_DIR%\VulkanSDK\Include\vulkan\vulkan.h" (
    set "VULKAN_SDK=%TOOLS_DIR%\VulkanSDK"
    set "PATH=%TOOLS_DIR%\VulkanSDK\Bin;%PATH%"
) else if exist "%TOOLS_DIR%\VulkanSDK" (
    for /d %%D in ("%TOOLS_DIR%\VulkanSDK\*") do if exist "%%D\Include\vulkan\vulkan.h" set "VULKAN_SDK=%%D"
    if defined VULKAN_SDK set "PATH=%VULKAN_SDK%\Bin;%PATH%"
)

exit /b 0
