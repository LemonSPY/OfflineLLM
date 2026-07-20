# Architecture

## Goals

- Native Windows chat app for a local LLM, GPU-accelerated on Intel Arc (and other Vulkan-capable GPUs).
- Two modes:
  - **Saved mode**: conversations persist across restarts, can be continued, archived, deleted.
  - **Offline mode**: a fully ephemeral session — nothing about the conversation or the model run touches disk, and closing it leaves no trace.
- Installable with one command: `setup.cmd` builds everything and drops a Desktop shortcut + Start Menu entry, no separate installer package.

## Why Python instead of a compiled native app

This started as a WinUI 3 (C#/.NET) app. That approach hit a wall: the Windows App SDK's unpackaged/self-contained build path turned out to depend on several MSBuild tasks (PRI resource generation, AppxPackage tooling) that are only shipped with a full Visual Studio install, not with a plain .NET SDK — exactly the kind of system-wide dependency this project set out to avoid. After working around several of those in turn, the app still crashed on launch with a WinUI-specific native activation failure with no clear single root cause. Rather than keep chasing an increasingly fragile toolchain, the app was rewritten in Python: a scripting language with mature, well-understood packaging (a plain `pip install` for dependencies, a standard installer that supports a true no-admin per-user install to a custom directory) and no dependency on Visual Studio at any point.

## Why offline mode doesn't use Docker

The original ask was for offline mode to run "inside a container on RAM/temp space that clears out after close, no trace of data." A literal Docker container was considered and rejected:

- Docker Desktop on Windows requires WSL2 and the Docker Desktop service — a heavy, separate install with its own licensing terms, background daemon, and GPU passthrough complexity (Arc GPU passthrough into a Linux container on Windows is not well supported).
- It adds a failure mode ("Docker isn't running") to what should be a one-click "start a private chat" action.

What actually matters for "ephemeral, no trace" is two things: (1) the conversation content and model working state never get written to persistent storage, and (2) the process and its memory are fully torn down when the session ends. Both are achievable without a container:

- **Offline sessions run `llama-server.exe` as a plain child process** (`subprocess.Popen`), bound to `127.0.0.1` on a randomly chosen port.
- **Conversation state for an offline session lives only in a Python list in `OfflineSessionEngine`** — it is never handed to `SqliteChatStore`, never logged, never written to a file. When the user closes the offline session (or the app), the process is killed and the list goes out of scope; there is nothing left to clean up because nothing was ever written.
- **The model weights file itself is opened read-only directly from wherever the user's model library lives** by `llama-server` (mmap) — we don't copy it into a RAM disk, because copying it would be a pointless extra write with no benefit: the model file is the same for every session (it's not sensitive per-conversation data).
- No prompts, completions, or KV-cache state from an offline session are ever written to the model cache, telemetry, or logs. `llama-server` is launched with `--log-disable` for offline sessions specifically, its stdout/stderr are discarded, and slot-to-disk saving is off by default already (there's no `--no-slot-save-path` flag — an earlier version of this code passed one, which made `llama-server` refuse to start at all; caught by testing offline mode directly rather than assuming it worked).
- **`--mlock` pins the model in physical RAM/VRAM for offline sessions** so the OS can never page any of it out to the Windows swap file — "0 trace" means nothing touches disk, not just that the app doesn't choose to write anything. Locking that much memory isn't always permitted (depends on the OS's working-set limits for the process), so `LlamaServerProcess.start()` falls back to running without it rather than failing the whole session over a hardening step.

This gets the actual property the user asked for — "close it and there's no trace" — without adding a Docker/WSL2 dependency.

## Layers

```
┌─────────────────────────────────────────────┐
│ app/ui  (CustomTkinter)                      │
│  - Chat window, mode switcher, model picker  │
│  - Saved-chat list (archive/delete)          │
└───────────────┬───────────────────────────────┘
                │ uses
┌───────────────▼───────────────────────────────┐
│ app/core  (Python)                            │
│  - LlamaServerProcess: spawn/monitor/kill     │
│    the native llama-server child process      │
│  - ModelManager: discover .gguf files,        │
│    track which model is active                │
│  - chat_engine: streams completions from      │
│    llama-server's OpenAI-compatible HTTP API   │
│  - SqliteChatStore: saved-mode persistence     │
│    (Python's built-in sqlite3, no dependency)  │
│  - OfflineSessionEngine: in-memory-only        │
│    session state for offline mode              │
│  - ModelDownloadService: streams a .gguf from  │
│    a URL straight into the models directory    │
└───────────────┬───────────────────────────────┘
                │ spawns + HTTP (localhost only)
┌───────────────▼───────────────────────────────┐
│ native/llama.cpp  (vendored, Vulkan backend)  │
│  - llama-server.exe does the actual GPU        │
│    inference (attention, quantized matmuls,    │
│    KV-cache) — the only third-party component  │
└─────────────────────────────────────────────┘
```

UI/network calls that block (starting `llama-server`, streaming a completion, downloading a model) always run on a background `threading.Thread`; results are marshalled back to the Tkinter main thread via `self.after(0, ...)`, since Tkinter widgets are not thread-safe to touch from a worker thread.

## Process lifecycle

1. App start: no inference process is running. The app is just a UI + SQLite-backed chat list.
2. User opens a saved chat or starts a new saved chat: `AppController` starts `llama-server.exe` once (lazily, on first use), pointed at the selected `.gguf` model. Subsequent saved chats reuse the same running server (it's stateless per-request from the server's point of view; conversation history is resent as context by `chat_engine`).
3. User opens "New offline chat": a separate `llama-server.exe` instance is started (same binary, same GPU flags), tagged as an offline-owned instance with logging disabled. `OfflineSessionEngine` owns the message list in memory.
4. User closes the offline session (or the whole app): the offline-owned server process is killed, its memory is freed by the OS, and the in-memory message list is cleared. If a saved-mode server is separately running it's unaffected.

## Model selection

Model choice is left to the user (swappable), not hardcoded. `ModelManager` scans a configurable models directory for `.gguf` files and lets the user pick which one `llama-server` loads. The picker surfaces file size so the user can judge fit against their GPU's 16GB budget (rule of thumb: pick a quantization whose file size is comfortably under the GPU memory budget, leaving room for KV-cache at the desired context length).

`model_catalog.CURATED` + `ModelDownloadService` back an in-app "Download models..." dialog: a short curated list of known-good instruction-tuned GGUF models (Qwen2.5 14B, Llama 3.1 8B, Mistral 7B, Phi-3.5 Mini) sized against a 16GB budget, or any direct `.gguf` URL the user pastes. Downloads stream straight into the models directory as `<name>.gguf.partial` and only get renamed to `<name>.gguf` once complete, so `ModelManager`'s `*.gguf` scan never picks up a truncated file from a cancelled or failed download.

## Repo-local dev toolchain

`tools/setup-workspace.cmd` provisions a portable, repo-scoped toolchain under `tools/` (gitignored) instead of requiring system-wide installs:

- **Python 3.13**, installed per-user into `tools/python` via the official installer's silent, non-admin, custom-`TargetDir` mode (`InstallAllUsers=0`) — includes tkinter (needed for the CustomTkinter UI; the alternative "embeddable" zip distribution deliberately excludes it) and pip, used to install `customtkinter` + `requests` from `app/requirements.txt`.
- **CMake** + **`w64devkit`** (portable GCC + Ninja + Make) — lets `build/build-llama.cmd` skip Visual Studio entirely and build llama.cpp with GCC/MinGW instead.
- **Vulkan SDK**, installed silently and scoped to `tools/VulkanSDK` — needed to compile llama.cpp's Vulkan backend (headers + the `glslc` shader compiler). Its "SDK Core" component unconditionally requires administrator rights for one install action with no CLI switch to skip it (confirmed against its own `--help` output and by testing `--nf`/`--no-force-installations`) — this is the one step in the whole setup that triggers a UAC prompt.

`tools/workspace-env.cmd` puts whichever of these exist onto `PATH` for the duration of a build script; if `tools/` hasn't been set up, the build scripts fall back to whatever's already installed system-wide.

## Install

`setup.cmd` installs a fully standalone copy — the portable Python interpreter (with `customtkinter`/`requests` already installed into it), the `app/` source, and the compiled `llama-server.exe` — into `%LocalAppData%\OfflineLlm\app`. The installed copy does not depend on the cloned repo or `tools/` afterward. A generated `OfflineLLM.cmd` launcher runs the app with `pythonw.exe` (no console window); Desktop and Start Menu shortcuts point at that launcher, created via a small generated VBScript that resolves the real (possibly OneDrive-redirected) special folder paths through `WScript.Shell.SpecialFolders` rather than assuming `%USERPROFILE%\Desktop`.
