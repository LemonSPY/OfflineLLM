@echo off
setlocal enabledelayedexpansion
REM Builds native\llama.cpp with the Vulkan GPU backend and copies llama-server.exe
REM (plus required DLLs) into src\OfflineLlm.App's output "engine" folder.
REM
REM The Vulkan backend is used (rather than Intel's SYCL/oneAPI backend) because it
REM works on Intel Arc GPUs (and most other GPUs) without requiring the separate
REM Intel oneAPI Base Toolkit install.
REM
REM PREREQUISITES
REM   - Visual Studio 2022 (or Build Tools) with "Desktop development with C++"
REM   - CMake >= 3.21 on PATH
REM   - Vulkan SDK (https://vulkan.lunarg.com/) with VULKAN_SDK environment variable set
REM   - git submodule already initialized: git submodule update --init --recursive
REM
REM USAGE
REM   build-llama.cmd [Release|Debug]

set "CONFIGURATION=%~1"
if "%CONFIGURATION%"=="" set "CONFIGURATION=Release"

set "REPO_ROOT=%~dp0.."
set "LLAMA_DIR=%REPO_ROOT%\native\llama.cpp"
set "BUILD_DIR=%LLAMA_DIR%\build-vulkan"
set "ENGINE_OUT_DIR=%REPO_ROOT%\src\OfflineLlm.App\bin\%CONFIGURATION%\net8.0-windows10.0.19041.0\win-x64\engine"

if not exist "%LLAMA_DIR%" (
    echo ERROR: native\llama.cpp not found. Run "git submodule update --init --recursive" first.
    exit /b 1
)

if "%VULKAN_SDK%"=="" (
    echo ERROR: VULKAN_SDK environment variable not set. Install the Vulkan SDK from https://vulkan.lunarg.com/ first.
    exit /b 1
)

echo Configuring llama.cpp with the Vulkan backend...
cmake -S "%LLAMA_DIR%" -B "%BUILD_DIR%" -G "Visual Studio 17 2022" -A x64 -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=%CONFIGURATION%
if errorlevel 1 (
    echo ERROR: cmake configure failed.
    exit /b 1
)

echo Building llama-server (this can take a while the first time)...
cmake --build "%BUILD_DIR%" --config %CONFIGURATION% --target llama-server -j
if errorlevel 1 (
    echo ERROR: cmake build failed.
    exit /b 1
)

set "BUILT_EXE_DIR=%BUILD_DIR%\bin\%CONFIGURATION%"
if not exist "%BUILT_EXE_DIR%\llama-server.exe" (
    echo ERROR: Build did not produce llama-server.exe at %BUILT_EXE_DIR%
    exit /b 1
)

echo Copying build output to %ENGINE_OUT_DIR%
if not exist "%ENGINE_OUT_DIR%" mkdir "%ENGINE_OUT_DIR%"
xcopy "%BUILT_EXE_DIR%\*" "%ENGINE_OUT_DIR%\" /E /I /Y >nul
if errorlevel 1 (
    echo ERROR: copying build output failed.
    exit /b 1
)

echo Done. llama-server.exe (Vulkan backend) is ready at %ENGINE_OUT_DIR%\llama-server.exe
exit /b 0
