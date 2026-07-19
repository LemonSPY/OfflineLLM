<#
.SYNOPSIS
    Builds native/llama.cpp with the Vulkan GPU backend and copies the resulting
    llama-server.exe (plus required DLLs) into src/OfflineLlm.App's output "engine" folder.

.DESCRIPTION
    The Vulkan backend is used (rather than Intel's SYCL/oneAPI backend) because it
    works on Intel Arc GPUs (and most other GPUs) without requiring the separate
    Intel oneAPI Base Toolkit install — one less prerequisite for users to install
    before the app works.

.PREREQUISITES
    - Visual Studio 2022 (or Build Tools) with "Desktop development with C++"
    - CMake >= 3.21 on PATH
    - Vulkan SDK (https://vulkan.lunarg.com/) with VULKAN_SDK environment variable set
    - git submodule already initialized: git submodule update --init --recursive
#>

[CmdletBinding()]
param(
    [ValidateSet("Release", "Debug")]
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$llamaDir = Join-Path $repoRoot "native\llama.cpp"
$buildDir = Join-Path $llamaDir "build-vulkan"
$engineOutDir = Join-Path $repoRoot "src\OfflineLlm.App\bin\$Configuration\net8.0-windows10.0.19041.0\win-x64\engine"

if (-not (Test-Path $llamaDir)) {
    throw "native/llama.cpp not found. Run 'git submodule update --init --recursive' first."
}

if (-not $env:VULKAN_SDK) {
    throw "VULKAN_SDK environment variable not set. Install the Vulkan SDK from https://vulkan.lunarg.com/ first."
}

Write-Host "Configuring llama.cpp with the Vulkan backend..." -ForegroundColor Cyan
cmake -S $llamaDir -B $buildDir `
    -G "Visual Studio 17 2022" -A x64 `
    -DGGML_VULKAN=ON `
    -DLLAMA_CURL=OFF `
    -DCMAKE_BUILD_TYPE=$Configuration

Write-Host "Building llama-server (this can take a while the first time)..." -ForegroundColor Cyan
cmake --build $buildDir --config $Configuration --target llama-server -j

$builtExeDir = Join-Path $buildDir "bin\$Configuration"
if (-not (Test-Path (Join-Path $builtExeDir "llama-server.exe"))) {
    throw "Build did not produce llama-server.exe at $builtExeDir"
}

Write-Host "Copying build output to $engineOutDir" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $engineOutDir | Out-Null
Copy-Item (Join-Path $builtExeDir "*") $engineOutDir -Recurse -Force

Write-Host "Done. llama-server.exe (Vulkan backend) is ready at $engineOutDir\llama-server.exe" -ForegroundColor Green
