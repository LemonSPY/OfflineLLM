# OfflineLLM

A native Windows desktop app for running local LLMs on your machine's GPU, with two chat modes:

- **Saved mode** — chats are persisted to a local SQLite database. Create, continue, archive, and delete conversations like a normal chat app.
- **Offline mode** — spins up a fresh, isolated inference session. All conversation state lives only in process memory (never written to disk), and the moment you close the offline session the model process is killed and every trace of that conversation is gone. Nothing is logged, cached, or swapped to disk.

Targets laptop iGPU/dGPU setups such as Intel Arc with 16GB of GPU memory, but works on any GPU llama.cpp's Vulkan backend supports.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design, including why offline mode is implemented as an in-memory-only session rather than a Docker container (no Docker/WSL2 dependency required).

Layers:

- **`native/llama.cpp`** — vendored inference engine (git submodule), built locally with the Vulkan backend so it runs on Intel Arc GPUs without requiring the Intel oneAPI toolkit. This is the only third-party component; it does the raw GPU matrix/attention math. Everything else in this repo is original code.
- **`src/OfflineLlm.Core`** — C# class library: manages the `llama-server` child process, model discovery/selection, chat storage (SQLite), and the in-memory-only offline session engine.
- **`src/OfflineLlm.App`** — WinUI 3 desktop app: chat UI, mode switcher, model picker, saved-chat list with archive/delete.
- **`installer/`** — WiX Toolset installer producing an MSI that installs the app, adds a Start Menu entry, and creates a desktop shortcut.

## Repo layout

```
native/llama.cpp/           git submodule, vendored inference engine
build/                      scripts to build llama.cpp with the Vulkan backend
src/OfflineLlm.Core/        chat storage, process management, offline session engine
src/OfflineLlm.App/         WinUI 3 desktop application
installer/                  WiX installer project
docs/                       architecture notes
```

## Building

Requires:

- .NET 8 SDK with the Windows App SDK / WinUI 3 workload
- Visual Studio 2022 (or Build Tools) with the "Desktop development with C++" workload, for building llama.cpp
- CMake and a Vulkan SDK, for building llama.cpp with the Vulkan backend
- WiX Toolset v4, for building the installer

```cmd
git submodule update --init --recursive
build\build-llama.cmd             REM builds native/llama.cpp with the Vulkan backend
dotnet build src\OfflineLlm.sln
installer\build-installer.cmd     REM produces installer\bin\OfflineLlm-Setup.msi
```

These are plain `.cmd` batch files (not PowerShell scripts) specifically so they run from `cmd.exe` or PowerShell without hitting PowerShell's script execution policy.

None of this has been compiled yet in this environment (no .NET SDK / CMake / Visual Studio available here) — build and smoke-test on a Windows dev machine with the above prerequisites before relying on it.
