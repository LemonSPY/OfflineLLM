<#
.SYNOPSIS
    Publishes OfflineLlm.App self-contained and packages it into an MSI with WiX v4.

.PREREQUISITES
    - .NET 8 SDK
    - WiX Toolset v4 CLI: dotnet tool install --global wix
    - build/build-llama.ps1 already run, so the app's publish output picks up
      engine\llama-server.exe (see AppPaths.LlamaServerExePath)

.OUTPUT
    installer/bin/OfflineLlm-Setup.msi
#>

[CmdletBinding()]
param(
    [ValidateSet("Release", "Debug")]
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$appProject = Join-Path $repoRoot "src\OfflineLlm.App\OfflineLlm.App.csproj"
$publishDir = Join-Path $repoRoot "installer\publish"
$iconPath = Join-Path $repoRoot "src\OfflineLlm.App\Assets\app.ico"
$outDir = Join-Path $PSScriptRoot "bin"

if (-not (Test-Path $iconPath)) {
    throw "Missing $iconPath — add a real app icon first (see src/OfflineLlm.App/Assets/README.md)."
}

Write-Host "Publishing OfflineLlm.App ($Configuration, self-contained win-x64)..." -ForegroundColor Cyan
dotnet publish $appProject `
    -c $Configuration `
    -r win-x64 `
    --self-contained true `
    -p:WindowsPackageType=None `
    -o $publishDir

Write-Host "Building MSI with WiX v4..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

wix build (Join-Path $PSScriptRoot "Product.wxs") `
    -d "AppPublishDir=$publishDir" `
    -d "AppIcon=$iconPath" `
    -arch x64 `
    -out (Join-Path $outDir "OfflineLlm-Setup.msi")

Write-Host "Done: $outDir\OfflineLlm-Setup.msi" -ForegroundColor Green
