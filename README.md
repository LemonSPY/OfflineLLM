# OfflineLLM

A native Windows desktop app for running local LLMs on your machine's GPU, with two chat modes:

- **Saved mode** — chats are persisted to a local SQLite database. Create, continue, archive, and delete conversations like a normal chat app.
- **Offline mode** — spins up a fresh, isolated inference session. All conversation state lives only in process memory (never written to disk), and the moment you close the offline session the model process is killed and every trace of that conversation is gone. Nothing is logged, cached, or swapped to disk.

Targets laptop iGPU/dGPU setups such as Intel Arc with 16GB of GPU memory, but works on any GPU llama.cpp's Vulkan backend supports.

In the app, click **Download models...** to pull a `.gguf` file straight from Hugging Face (a small curated list is built in, or paste any direct `.gguf` URL) — no manual file wrangling required.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design, including why offline mode is implemented as an in-memory-only session rather than a Docker container (no Docker/WSL2 dependency required).

Layers:

- **`native/llama.cpp`** — vendored inference engine (git submodule), built locally with the Vulkan backend so it runs on Intel Arc GPUs without requiring the Intel oneAPI toolkit. This is the only third-party component; it does the raw GPU matrix/attention math. Everything else in this repo is original code.
- **`app/core`** — Python: manages the `llama-server` child process, model discovery/selection/download, chat storage (SQLite via the standard library), and the in-memory-only offline session engine.
- **`app/ui`** — CustomTkinter desktop UI: chat window, mode switcher, model picker, saved-chat list with archive/delete.

## Install (one command)

```cmd
git clone --recurse-submodules <this repo>
cd OFFLINELLM
setup.cmd
```

That's the entire install. `setup.cmd` is the single entry point at the repo root and does everything, with a numbered `[Step N/5]` banner before each stage so it's clear what's happening and where it is if something fails:

1. Fetches the `native/llama.cpp` submodule
2. Provisions a portable, repo-local build toolchain into `tools\` (first run only — see below)
3. Compiles llama.cpp with the Vulkan GPU backend
4. Installs a standalone copy of Python + the app + the compiled engine into `%LocalAppData%\OfflineLlm\app` (the installed copy doesn't depend on the repo afterward — you can delete the cloned folder and the installed app keeps working)
5. Creates a **Desktop shortcut** and a **Start Menu entry**, then **launches the app**

No admin rights needed for the app itself, nothing is installed system-wide, and nothing outside `tools\` and `%LocalAppData%\OfflineLlm` is touched. Re-running `setup.cmd` is safe — each step skips work that's already done (e.g. it won't re-download the toolchain or recompile llama.cpp from scratch).

You do **not** need a system-wide Python, Visual Studio, CMake, or the Vulkan SDK — step 2 downloads portable copies of all of that (~1-1.5GB, one time) confined to `tools\`. The only step that needs your one-time approval is a UAC prompt for the Vulkan SDK's installer (its "SDK Core" component unconditionally requires it for one install action — there's no way to script around it, see `tools/setup-workspace.cmd`'s comments). Everything else here is a plain `.cmd` batch file, never PowerShell, so nothing hits PowerShell's script execution policy.

## Repo layout

```
setup.cmd                    the one command that builds and installs everything
native/llama.cpp/            git submodule, vendored inference engine
tools/                       one-time setup script + repo-local portable toolchain (gitignored)
build/                       scripts to build llama.cpp with the Vulkan backend
app/core/                    chat storage, process management, offline session engine, model downloads
app/ui/                      CustomTkinter desktop UI
app/main.py                  entry point
docs/                        architecture notes
```

## Manual / advanced setup

If you'd rather use tools you already have installed system-wide, the build scripts fall back to whatever's on PATH when `tools\` isn't present:

```cmd
git submodule update --init --recursive
build\build-llama.cmd             REM needs CMake + Vulkan SDK + a C/C++ compiler on PATH
python -m pip install -r app\requirements.txt
python app\main.py
```

None of this has been compiled/run in this exact form yet in this environment — `setup.cmd` is the tested, known-working path.
