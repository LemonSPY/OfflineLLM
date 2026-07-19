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

In the app, click **Download models...** to pull a `.gguf` file straight from Hugging Face (a small curated list is built in, or paste any direct `.gguf` URL) — no manual file wrangling required.

## Repo layout

```
native/llama.cpp/           git submodule, vendored inference engine
tools/                       one-time setup script + repo-local portable toolchain (gitignored)
build/                      scripts to build llama.cpp with the Vulkan backend
src/OfflineLlm.Core/        chat storage, process management, offline session engine, model downloads
src/OfflineLlm.App/         WinUI 3 desktop application
installer/                  WiX installer project
docs/                       architecture notes
```

## Building

You do **not** need to install Visual Studio, a system-wide .NET SDK, CMake, or the Vulkan SDK. One script provisions a portable, repo-local copy of everything needed, entirely inside `tools\` (nothing touches Program Files, PATH, or the registry):

```cmd
git clone --recurse-submodules <this repo>
cd OFFLINELLM
tools\setup-workspace.cmd         REM one-time, downloads ~1-1.5GB into tools\
build\build-llama.cmd             REM builds native/llama.cpp with the Vulkan backend
installer\build-installer.cmd     REM publishes the app + produces installer\bin\OfflineLlm-Setup.msi
```

Run `installer\bin\OfflineLlm-Setup.msi` and it installs the app under `%LocalAppData%\OfflineLlm`, with a Start Menu entry and a Desktop shortcut. Everything is a plain `.cmd` batch file (never PowerShell), so nothing hits PowerShell's script execution policy.

`tools\setup-workspace.cmd` installs (all repo-local, under `tools\`):

- **.NET 8 SDK** — to build the WinUI 3 app
- **CMake** + **w64devkit** (a portable GCC + Ninja + Make toolchain) — to build llama.cpp *without* needing Visual Studio at all
- **Vulkan SDK** — headers + shader compiler needed to build llama.cpp's Vulkan backend (end users don't need this installed — the Vulkan *runtime* they need already ships with their GPU driver)
- **WiX v4 CLI** — as a local dotnet tool, to build the MSI

If you'd rather use tools you already have installed system-wide (a full Visual Studio, a system .NET SDK, etc.), the build scripts fall back to whatever's on PATH when `tools\` isn't present — skip `setup-workspace.cmd` in that case.

Prefer to build with Visual Studio and the standard Vulkan SDK installer instead of the portable toolchain? That still works — just install .NET 8 SDK + Windows App SDK workload, Visual Studio 2022 (C++ workload), CMake, and the Vulkan SDK yourself, then run `build\build-llama.cmd` / `installer\build-installer.cmd` as above; they'll detect there's no `tools\` toolchain and use your system installs.

None of this has been compiled yet — these scripts are written and ready to run but haven't been executed end-to-end. Building and smoke-testing is the next step.
