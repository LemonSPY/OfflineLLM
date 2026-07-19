# Architecture

## Goals

- Native Windows chat app for a local LLM, GPU-accelerated on Intel Arc (and other Vulkan-capable GPUs).
- Two modes:
  - **Saved mode**: conversations persist across restarts, can be continued, archived, deleted.
  - **Offline mode**: a fully ephemeral session — nothing about the conversation or the model run touches disk, and closing it leaves no trace.
- Installable like a normal Windows app: MSI installer, Start Menu entry, desktop shortcut.

## Why offline mode doesn't use Docker

The original ask was for offline mode to run "inside a container on RAM/temp space that clears out after close, no trace of data." A literal Docker container was considered and rejected:

- Docker Desktop on Windows requires WSL2 and the Docker Desktop service — a heavy, separate install with its own licensing terms, background daemon, and GPU passthrough complexity (Arc GPU passthrough into a Linux container on Windows is not well supported).
- It adds a failure mode ("Docker isn't running") to what should be a one-click "start a private chat" action.

What actually matters for "ephemeral, no trace" is two things: (1) the conversation content and model working state never get written to persistent storage, and (2) the process and its memory are fully torn down when the session ends. Both are achievable without a container:

- **Offline sessions run `llama-server.exe` as a plain child process**, bound to `127.0.0.1` on a randomly chosen port, with a working directory pointed at the OS temp folder (which itself is not persisted across reboots, but we don't even rely on that — see below).
- **Conversation state for an offline session lives only in .NET objects in `OfflineSessionEngine`** (an in-memory list of messages) — it is never handed to `ChatStore`/SQLite, never logged, never written to a file. When the user closes the offline session (or the app), the process is killed and the objects are garbage collected; there is nothing left to clean up because nothing was ever written.
- **The model weights file itself is opened read-only (mmap) directly from wherever the user's model library lives** — we don't copy it into a RAM disk, because copying it would be a pointless extra write with no benefit: the model file is the same for every session (it's not sensitive per-conversation data), and mmap'd reads already stay in the OS page cache without us needing to manage a virtual disk.
- No prompts, completions, or KV-cache state from an offline session are ever written to the model cache, telemetry, or logs. `llama-server` is launched with logging directed to a null sink for offline sessions specifically.

This gets the actual property the user asked for — "close it and there's no trace" — without adding a Docker/WSL2 dependency. If true disk-level RAM-backed isolation is wanted later (e.g. to also guard against the model file's OS-level page cache metadata), an `ImDisk`-backed temp mount is a self-contained fallback that doesn't require Docker either — but it's not needed for the current requirement and isn't implemented.

## Layers

```
┌─────────────────────────────────────────────┐
│ OfflineLlm.App  (WinUI 3)                    │
│  - Chat UI, mode switcher, model picker      │
│  - Saved-chat list (archive/delete)          │
└───────────────┬───────────────────────────────┘
                │ uses
┌───────────────▼───────────────────────────────┐
│ OfflineLlm.Core  (C# class library)          │
│  - LlamaServerProcess: spawn/monitor/kill     │
│    the native llama-server child process      │
│  - ModelManager: discover .gguf files,        │
│    track which model is active                │
│  - ChatEngine: streams completions from        │
│    llama-server's OpenAI-compatible HTTP API   │
│  - ChatStore (SQLite): saved-mode persistence  │
│  - OfflineSessionEngine: in-memory-only        │
│    session state for offline mode              │
└───────────────┬───────────────────────────────┘
                │ spawns + HTTP (localhost only)
┌───────────────▼───────────────────────────────┐
│ native/llama.cpp  (vendored, Vulkan backend)  │
│  - llama-server.exe does the actual GPU        │
│    inference (attention, quantized matmuls,    │
│    KV-cache) — the only third-party component  │
└─────────────────────────────────────────────┘
```

## Process lifecycle

1. App start: no inference process is running. The app is just a UI + SQLite-backed chat list.
2. User opens a saved chat or starts a new saved chat: `LlamaServerProcess` starts `llama-server.exe` once (lazily, on first use), pointed at the selected `.gguf` model, with `-ngl <n>` to offload layers to the Vulkan GPU device. Subsequent saved chats reuse the same running server (it's stateless per-request from the server's point of view; conversation history is resent as context by `ChatEngine`).
3. User opens "New offline chat": if no server is running, `LlamaServerProcess` starts one (same binary, same GPU flags), tagged as an offline-owned instance with logging disabled. `OfflineSessionEngine` owns the message list in memory.
4. User closes the offline session (or the whole app): the offline-owned server process is killed, its memory is freed by the OS, and the in-memory message list goes out of scope. If a saved-mode server is separately running it's unaffected; if it was the same shared instance and no saved chat is active, it's killed too so nothing lingers.

## Model selection

Model choice is left to the user (swappable), not hardcoded. `ModelManager` scans a configurable models directory for `.gguf` files and lets the user pick which one `llama-server` loads. The picker surfaces file size so the user can judge fit against their GPU's 16GB budget (rule of thumb: pick a quantization whose file size is comfortably under the GPU memory budget, leaving room for KV-cache at the desired context length).

`ModelCatalog` + `ModelDownloadService` add an in-app "Download models..." dialog: a short curated list of known-good instruction-tuned GGUF models (Qwen2.5 14B, Llama 3.1 8B, Mistral 7B, Phi-3.5 Mini) sized against a 16GB budget, or any direct `.gguf` URL the user pastes. Downloads stream straight into the models directory as `<name>.gguf.partial` and only get renamed to `<name>.gguf` once complete, so `ModelManager`'s `*.gguf` scan never picks up a truncated file from a cancelled or failed download.

## Repo-local dev toolchain

`tools/setup-workspace.cmd` provisions a portable, repo-scoped toolchain under `tools/` (gitignored) instead of requiring system-wide installs: a local .NET 8 SDK, CMake, `w64devkit` (portable GCC + Ninja + Make — this is what lets `build/build-llama.cmd` skip Visual Studio entirely and build llama.cpp with GCC/MinGW instead), a locally-scoped Vulkan SDK install, and the WiX v4 CLI as a local dotnet tool. `tools/workspace-env.cmd` puts whichever of these exist onto PATH for the duration of a build script; if `tools/` hasn't been set up, the build scripts fall back to whatever's already installed system-wide (a full Visual Studio, a system .NET SDK, etc.).

## Installer

WiX Toolset v4 produces an MSI that:

- installs `OfflineLlm.App` (published, self-contained) plus the built `native/llama.cpp` Vulkan binaries into `%ProgramFiles%\OfflineLlm`
- registers a Start Menu shortcut
- registers a Desktop shortcut
- registers an uninstall entry in Add/Remove Programs
