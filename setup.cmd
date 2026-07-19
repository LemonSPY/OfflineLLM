@echo off
setlocal enabledelayedexpansion
title OfflineLLM Setup

REM Single entry point: clone the repo, run this, done.
REM   1. pulls in native/llama.cpp (git submodule)
REM   2. provisions a repo-local portable build toolchain (tools\setup-workspace.cmd)
REM   3. compiles llama.cpp with the Vulkan GPU backend
REM   4. publishes the app (self-contained, includes the compiled engine)
REM   5. installs it to %LocalAppData%\OfflineLlm\app
REM   6. creates a Desktop shortcut and a Start Menu entry
REM   7. launches the app
REM
REM Nothing here needs admin rights and nothing is installed system-wide -
REM nothing outside tools\ (portable build toolchain) and %LocalAppData%\OfflineLlm
REM (the installed app + your chats/models) is touched.
REM
REM Re-running is safe: each step skips work that's already done.

set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"
set "INSTALL_DIR=%LocalAppData%\OfflineLlm\app"
set "PUBLISH_DIR=%REPO_ROOT%\_setup-publish"
set "TOTAL_STEPS=6"

call :banner 1 "Fetching native/llama.cpp submodule"
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: git is not on PATH. Install Git for Windows first: https://git-scm.com/download/win
    goto :fail
)
git -C "%REPO_ROOT%" submodule update --init --recursive
if errorlevel 1 goto :fail

call :banner 2 "Provisioning the portable build toolchain (first run downloads ~1-1.5GB)"
call "%REPO_ROOT%\tools\setup-workspace.cmd"
if errorlevel 1 goto :fail

call :banner 3 "Building the local inference engine (llama.cpp, Vulkan backend)"
call "%REPO_ROOT%\build\build-llama.cmd" Release
if errorlevel 1 goto :fail

call :banner 4 "Publishing OfflineLLM"
call "%REPO_ROOT%\tools\workspace-env.cmd"
if exist "%PUBLISH_DIR%" rmdir /s /q "%PUBLISH_DIR%"
dotnet publish "%REPO_ROOT%\src\OfflineLlm.App\OfflineLlm.App.csproj" ^
    -c Release -r win-x64 --self-contained true -p:Platform=x64 -p:WindowsPackageType=None ^
    -o "%PUBLISH_DIR%"
if errorlevel 1 goto :fail

call :banner 5 "Installing to %INSTALL_DIR%"
if exist "%INSTALL_DIR%" (
    echo Removing previous install...
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"
xcopy "%PUBLISH_DIR%\*" "%INSTALL_DIR%\" /E /I /Y >nul
if errorlevel 1 goto :fail
rmdir /s /q "%PUBLISH_DIR%"

call :banner 6 "Creating shortcuts"
call :make_shortcut "%INSTALL_DIR%\OfflineLlm.App.exe" "%USERPROFILE%\Desktop\OfflineLLM.lnk" "%INSTALL_DIR%"
call :make_shortcut "%INSTALL_DIR%\OfflineLlm.App.exe" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\OfflineLLM.lnk" "%INSTALL_DIR%"

echo.
echo ============================================================
echo   Setup complete.
echo   Installed to : %INSTALL_DIR%
echo   Shortcuts    : Desktop and Start Menu
echo   Your data    : %LocalAppData%\OfflineLlm\chats.db, %LocalAppData%\OfflineLlm\models\
echo ============================================================
echo Launching OfflineLLM...
start "" "%INSTALL_DIR%\OfflineLlm.App.exe"
exit /b 0

:banner
echo.
echo ============================================================
echo   [Step %~1/%TOTAL_STEPS%] %~2
echo ============================================================
exit /b 0

:make_shortcut
REM %1=target exe  %2=shortcut .lnk path  %3=working directory
set "SHORTCUT_TARGET=%~1"
set "SHORTCUT_PATH=%~2"
set "SHORTCUT_WORKDIR=%~3"
set "VBS=%TEMP%\_offlinellm_mkshortcut_%RANDOM%.vbs"
> "%VBS%" echo Set oWS = WScript.CreateObject("WScript.Shell")
>>"%VBS%" echo sLinkFile = "%SHORTCUT_PATH%"
>>"%VBS%" echo Set oLink = oWS.CreateShortcut(sLinkFile)
>>"%VBS%" echo oLink.TargetPath = "%SHORTCUT_TARGET%"
>>"%VBS%" echo oLink.WorkingDirectory = "%SHORTCUT_WORKDIR%"
>>"%VBS%" echo oLink.IconLocation = "%SHORTCUT_TARGET%"
>>"%VBS%" echo oLink.Save
cscript //nologo "%VBS%"
del "%VBS%" >nul 2>nul
echo Created %SHORTCUT_PATH%
exit /b 0

:fail
echo.
echo ============================================================
echo   Setup FAILED at the step above - see the error message.
echo ============================================================
exit /b 1
