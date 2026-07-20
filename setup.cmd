@echo off
setlocal enabledelayedexpansion
title OfflineLLM Setup

REM Single entry point: clone the repo, run this, done.
REM   1. pulls in native/llama.cpp (git submodule)
REM   2. provisions a repo-local portable build toolchain, including Python
REM      (tools\setup-workspace.cmd)
REM   3. compiles llama.cpp with the Vulkan GPU backend
REM   4. installs a standalone copy of Python + the app + the compiled
REM      engine into %LocalAppData%\OfflineLlm\app
REM   5. creates a Desktop shortcut and a Start Menu entry, then launches it
REM
REM Nothing here needs admin rights and nothing is installed system-wide -
REM nothing outside tools\ (portable build toolchain) and %LocalAppData%\OfflineLlm
REM (the installed app + your chats/models) is touched.
REM
REM Re-running is safe: each step skips work that's already done.

set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"
set "INSTALL_DIR=%LocalAppData%\OfflineLlm\app"
set "TOTAL_STEPS=5"

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

call :banner 4 "Installing to %INSTALL_DIR%"
if exist "%INSTALL_DIR%" (
    echo Removing previous install...
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"

echo Copying Python runtime...
xcopy "%REPO_ROOT%\tools\python\*" "%INSTALL_DIR%\python\" /E /I /Y >nul
if errorlevel 1 goto :fail

echo Copying app files (including the compiled inference engine)...
xcopy "%REPO_ROOT%\app\*" "%INSTALL_DIR%\app\" /E /I /Y >nul
if errorlevel 1 goto :fail

call :write_launcher
if errorlevel 1 goto :fail

call :banner 5 "Creating shortcuts"
call :make_shortcut "%INSTALL_DIR%\OfflineLLM.vbs" Desktop "%INSTALL_DIR%"
if errorlevel 1 goto :fail
call :make_shortcut "%INSTALL_DIR%\OfflineLLM.vbs" Programs "%INSTALL_DIR%"
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo   Setup complete.
echo   Installed to : %INSTALL_DIR%
echo   Shortcuts    : Desktop and Start Menu
echo   Your data    : %LocalAppData%\OfflineLlm\chats.db, %LocalAppData%\OfflineLlm\models\
echo ============================================================
echo Launching OfflineLLM...
wscript //nologo "%INSTALL_DIR%\OfflineLLM.vbs"
exit /b 0

:banner
echo.
echo ============================================================
echo   [Step %~1/%TOTAL_STEPS%] %~2
echo ============================================================
exit /b 0

REM Writes a tiny launcher that runs the app with pythonw.exe. This has to be
REM a .vbs (run via wscript.exe with window style 0), not a .cmd batch file -
REM a .cmd always opens its own visible console host window, and that window
REM stays open indefinitely after `start`, defeating the point of using
REM pythonw.exe (no console) in the first place (confirmed: this happened).
REM WshShell.Run with the visibility flag set to 0 launches with no window
REM of any kind.
:write_launcher
> "%INSTALL_DIR%\OfflineLLM.vbs" echo Set oWS = WScript.CreateObject("WScript.Shell")
>>"%INSTALL_DIR%\OfflineLLM.vbs" echo oWS.CurrentDirectory = "%INSTALL_DIR%\app"
>>"%INSTALL_DIR%\OfflineLLM.vbs" echo oWS.Run """%INSTALL_DIR%\python\pythonw.exe"" main.py", 0, False
exit /b 0

:make_shortcut
REM %1=target  %2=WScript.Shell SpecialFolders name (e.g. Desktop, Programs)
REM %3=working directory
REM Special folders (not %USERPROFILE%\Desktop) because Desktop/Documents/etc. are
REM commonly redirected elsewhere (OneDrive, folder redirection policy, ...) -
REM WshShell.SpecialFolders resolves wherever they actually are.
set "SHORTCUT_TARGET=%~1"
set "SPECIAL_FOLDER=%~2"
set "SHORTCUT_WORKDIR=%~3"
set "VBS=%TEMP%\_offlinellm_mkshortcut_%RANDOM%.vbs"
> "%VBS%" echo Set oWS = WScript.CreateObject("WScript.Shell")
>>"%VBS%" echo sLinkFile = oWS.SpecialFolders("%SPECIAL_FOLDER%") ^& "\OfflineLLM.lnk"
>>"%VBS%" echo Set oLink = oWS.CreateShortcut(sLinkFile)
>>"%VBS%" echo oLink.TargetPath = "%SHORTCUT_TARGET%"
>>"%VBS%" echo oLink.WorkingDirectory = "%SHORTCUT_WORKDIR%"
>>"%VBS%" echo oLink.IconLocation = "%INSTALL_DIR%\app\assets\app.ico"
>>"%VBS%" echo oLink.Save
>>"%VBS%" echo WScript.Echo sLinkFile
for /f "usebackq delims=" %%P in (`cscript //nologo "%VBS%"`) do set "CREATED_LNK_PATH=%%P"
del "%VBS%" >nul 2>nul
if not exist "%CREATED_LNK_PATH%" (
    echo ERROR: failed to create shortcut in special folder "%SPECIAL_FOLDER%".
    exit /b 1
)
echo Created %CREATED_LNK_PATH%
exit /b 0

:fail
echo.
echo ============================================================
echo   Setup FAILED at the step above - see the error message.
echo ============================================================
exit /b 1
