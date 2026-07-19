@echo off
setlocal enabledelayedexpansion
REM Builds native\llama.cpp with the Vulkan GPU backend and copies llama-server.exe
REM (plus required DLLs) into src\OfflineLlm.App\Engine\ - a source-tracked (but
REM gitignored-content) folder that OfflineLlm.App.csproj copies into the app's
REM output/publish directory automatically, so this only needs to run once and
REM every later `dotnet build`/`dotnet publish` just picks it up.
REM
REM The Vulkan backend is used (rather than Intel's SYCL/oneAPI backend) because it
REM works on Intel Arc GPUs (and most other GPUs) without requiring the separate
REM Intel oneAPI Base Toolkit install.
REM
REM By default this uses the repo-local portable toolchain from
REM tools\setup-workspace.cmd (w64devkit's GCC + Ninja + the local Vulkan SDK) so
REM no Visual Studio install is required. If tools\ hasn't been set up, it falls
REM back to whatever CMake/Vulkan SDK/Visual Studio is already on your system.
REM
REM PREREQUISITES (pick one)
REM   A) run tools\setup-workspace.cmd once (recommended - no other installs needed)
REM   B) have CMake, the Vulkan SDK, and Visual Studio 2022 (C++ workload) on PATH
REM
REM   Either way: git submodule update --init --recursive must have been run first.
REM
REM USAGE
REM   build-llama.cmd [Release|Debug]

set "CONFIGURATION=%~1"
if "%CONFIGURATION%"=="" set "CONFIGURATION=Release"

set "REPO_ROOT=%~dp0.."
set "LLAMA_DIR=%REPO_ROOT%\native\llama.cpp"
set "BUILD_DIR=%LLAMA_DIR%\build-vulkan"
set "ENGINE_OUT_DIR=%REPO_ROOT%\src\OfflineLlm.App\Engine"

if not exist "%LLAMA_DIR%" (
    echo ERROR: native\llama.cpp not found. Run "git submodule update --init --recursive" first.
    exit /b 1
)

call "%REPO_ROOT%\tools\workspace-env.cmd"

set "USE_LOCAL_TOOLCHAIN=0"
if exist "%REPO_ROOT%\tools\w64devkit\bin\gcc.exe" if exist "%REPO_ROOT%\tools\w64devkit\bin\ninja.exe" (
    set "USE_LOCAL_TOOLCHAIN=1"
)

if "%VULKAN_SDK%"=="" (
    echo ERROR: VULKAN_SDK not set. Run tools\setup-workspace.cmd, or install the
    echo        Vulkan SDK from https://vulkan.lunarg.com/ and set VULKAN_SDK yourself.
    exit /b 1
)

if "%USE_LOCAL_TOOLCHAIN%"=="1" (
    echo Configuring llama.cpp with the Vulkan backend using the local w64devkit/Ninja toolchain...
    set "BUILT_EXE_DIR=%BUILD_DIR%\bin"
    cmake -S "%LLAMA_DIR%" -B "%BUILD_DIR%" -G "Ninja" ^
        -DCMAKE_C_COMPILER="%REPO_ROOT%\tools\w64devkit\bin\gcc.exe" ^
        -DCMAKE_CXX_COMPILER="%REPO_ROOT%\tools\w64devkit\bin\g++.exe" ^
        -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=%CONFIGURATION%
) else (
    echo Configuring llama.cpp with the Vulkan backend using Visual Studio...
    set "BUILT_EXE_DIR=%BUILD_DIR%\bin\%CONFIGURATION%"
    cmake -S "%LLAMA_DIR%" -B "%BUILD_DIR%" -G "Visual Studio 17 2022" -A x64 ^
        -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=%CONFIGURATION%
)
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
