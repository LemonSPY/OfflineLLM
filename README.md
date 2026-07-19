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

## Install (one command)

```cmd
git clone --recurse-submodules <this repo>
cd OFFLINELLM
setup.cmd
```

That's the entire install. `setup.cmd` is the single entry point at the repo root and does everything, with a numbered `[Step N/6]` banner before each stage so it's clear what's happening and where it is if something fails:

1. Fetches the `native/llama.cpp` submodule
2. Provisions a portable, repo-local build toolchain into `tools\` (first run only — see below)
3. Compiles llama.cpp with the Vulkan GPU backend
4. Publishes the app (self-contained, with the compiled engine bundled in)
5. Installs it to `%LocalAppData%\OfflineLlm\app`
6. Creates a **Desktop shortcut** and a **Start Menu entry**, then **launches the app**

No admin rights needed, nothing is installed system-wide, and nothing outside `tools\` and `%LocalAppData%\OfflineLlm` is touched. Re-running `setup.cmd` is safe — each step skips work that's already done (e.g. it won't re-download the toolchain or recompile llama.cpp from scratch).

You do **not** need Visual Studio, a system-wide .NET SDK, CMake, or the Vulkan SDK — step 2 downloads portable copies of all of that (~1-1.5GB, one time) confined to `tools\`. Everything here is a plain `.cmd` batch file, never PowerShell, so nothing hits PowerShell's script execution policy.

## Repo layout

```
setup.cmd                    the one command that builds and installs everything
native/llama.cpp/            git submodule, vendored inference engine
tools/                       one-time setup script + repo-local portable toolchain (gitignored)
build/                       scripts to build llama.cpp with the Vulkan backend
src/OfflineLlm.Core/         chat storage, process management, offline session engine, model downloads
src/OfflineLlm.App/          WinUI 3 desktop application
installer/                   WiX installer project (produces a distributable MSI - optional, see below)
docs/                        architecture notes
```

## Building an MSI instead (optional)

`setup.cmd` installs straight to `%LocalAppData%` for you, on this machine. If you instead want a distributable `.msi` to hand to someone else, use the WiX-based installer project after the same first two steps:

```cmd
git clone --recurse-submodules <this repo>
cd OFFLINELLM
tools\setup-workspace.cmd         REM one-time, downloads ~1-1.5GB into tools\
build\build-llama.cmd             REM builds native/llama.cpp with the Vulkan backend
installer\build-installer.cmd     REM produces installer\bin\OfflineLlm-Setup.msi
```

Running that MSI installs the app under `%LocalAppData%\OfflineLlm`, with the same Start Menu entry and Desktop shortcut.

`tools\setup-workspace.cmd` installs (all repo-local, under `tools\`):

- **.NET 8 SDK** — to build the WinUI 3 app
- **CMake** + **w64devkit** (a portable GCC + Ninja + Make toolchain) — to build llama.cpp *without* needing Visual Studio at all
- **Vulkan SDK** — headers + shader compiler needed to build llama.cpp's Vulkan backend (end users don't need this installed — the Vulkan *runtime* they need already ships with their GPU driver)
- **WiX v4 CLI** — as a local dotnet tool, to build the MSI

If you'd rather use tools you already have installed system-wide (a full Visual Studio, a system .NET SDK, etc.), the build scripts fall back to whatever's on PATH when `tools\` isn't present — skip `setup-workspace.cmd` in that case, and install .NET 8 SDK + Windows App SDK workload, Visual Studio 2022 (C++ workload), CMake, and the Vulkan SDK yourself first.

None of this has been compiled yet — these scripts are written and ready to run but haven't been executed end-to-end. Running `setup.cmd` for the first time is the next step.
