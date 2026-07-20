"""Main application window: sidebar of saved chats + mode switcher, chat
panel, model picker.

Network/process calls (starting llama-server, streaming completions) block,
so they always run on a background thread; results are marshalled back to
the Tkinter main thread via `self.after(0, ...)`, which is the only
thread-safe way to touch Tkinter/CustomTkinter widgets.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core.app_controller import AppController, ChatMode
from core.chat_models import ChatSession, ChatSessionStatus
from core.model_manager import ModelInfo

from .download_dialog import DownloadModelsDialog


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OfflineLLM")
        self.geometry("1100x720")

        self.controller = AppController()
        self._show_archived = tk.BooleanVar(value=False)
        self._selected_model: ModelInfo | None = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_layout()
        self._refresh_models()
        self._refresh_saved_sessions()

    # -- Layout -----------------------------------------------------

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=280)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="OfflineLLM", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, padx=12, pady=(16, 8), sticky="w"
        )

        button_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        button_row.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="we")
        ctk.CTkButton(button_row, text="New saved chat", command=self._on_new_saved_chat).pack(
            side="left", expand=True, fill="x", padx=(0, 4)
        )
        ctk.CTkButton(button_row, text="New offline chat", command=self._on_new_offline_chat).pack(
            side="left", expand=True, fill="x", padx=(4, 0)
        )

        self._sessions_frame = ctk.CTkScrollableFrame(sidebar)
        self._sessions_frame.grid(row=2, column=0, padx=12, pady=8, sticky="nswe")

        ctk.CTkCheckBox(
            sidebar, text="Show archived", variable=self._show_archived,
            command=self._refresh_saved_sessions,
        ).grid(row=3, column=0, padx=12, pady=(0, 12), sticky="w")

        # -- Chat panel -----------------------------------------------------
        chat_panel = ctk.CTkFrame(self, fg_color="transparent")
        chat_panel.grid(row=0, column=1, sticky="nswe", padx=16, pady=16)
        chat_panel.grid_columnconfigure(0, weight=1)
        chat_panel.grid_rowconfigure(1, weight=1)

        top_row = ctk.CTkFrame(chat_panel, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="we", pady=(0, 8))

        self._mode_label = ctk.CTkLabel(top_row, text="No chat open", font=ctk.CTkFont(size=15, weight="bold"))
        self._mode_label.pack(side="left")

        self._model_picker = ctk.CTkOptionMenu(top_row, values=["No models found"], command=self._on_model_selected)
        self._model_picker.pack(side="left", padx=12)

        ctk.CTkButton(top_row, text="Download models...", command=self._on_download_models).pack(side="left")

        self._messages_box = ctk.CTkTextbox(chat_panel, wrap="word", state="disabled")
        self._messages_box.grid(row=1, column=0, sticky="nswe", pady=(0, 8))

        input_row = ctk.CTkFrame(chat_panel, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="we")
        input_row.grid_columnconfigure(0, weight=1)

        self._message_input = ctk.CTkEntry(input_row, placeholder_text="Message...")
        self._message_input.grid(row=0, column=0, sticky="we", padx=(0, 8))
        self._message_input.bind("<Return>", lambda _e: self._on_send())

        self._send_button = ctk.CTkButton(input_row, text="Send", width=80, command=self._on_send)
        self._send_button.grid(row=0, column=1)

    # -- Models -----------------------------------------------------

    def _refresh_models(self) -> None:
        models = self.controller.list_available_models()
        self._models_by_name = {m.display_name: m for m in models}

        if models:
            self._model_picker.configure(values=list(self._models_by_name.keys()))
            if self._selected_model is None or self._selected_model.id not in {m.id for m in models}:
                self._selected_model = models[0]
                self._model_picker.set(models[0].display_name)
        else:
            self._model_picker.configure(values=["No models found"])
            self._model_picker.set("No models found")
            self._selected_model = None

    def _on_model_selected(self, display_name: str) -> None:
        self._selected_model = self._models_by_name.get(display_name)

    # -- Saved sessions list -----------------------------------------------------

    def _refresh_saved_sessions(self) -> None:
        for child in self._sessions_frame.winfo_children():
            child.destroy()

        sessions = self.controller.list_saved_sessions(self._show_archived.get())
        for session in sessions:
            self._add_session_row(session)

    def _add_session_row(self, session: ChatSession) -> None:
        row = ctk.CTkFrame(self._sessions_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=1)

        label_text = session.title
        if session.status is ChatSessionStatus.ARCHIVED:
            label_text += " (archived)"

        label = ctk.CTkLabel(row, text=label_text, anchor="w", cursor="hand2")
        label.grid(row=0, column=0, sticky="we")
        label.bind("<Button-1>", lambda _e, sid=session.id: self._on_open_saved_chat(sid))

        menu_button = ctk.CTkButton(row, text="⋮", width=28, command=lambda: self._show_session_menu(session))
        menu_button.grid(row=0, column=1)

    def _show_session_menu(self, session: ChatSession) -> None:
        menu = tk.Menu(self, tearoff=0)
        archive_label = "Unarchive" if session.status is ChatSessionStatus.ARCHIVED else "Archive"
        menu.add_command(
            label=archive_label,
            command=lambda: self._on_archive_session(session.id, session.status is not ChatSessionStatus.ARCHIVED),
        )
        menu.add_command(label="Delete", command=lambda: self._on_delete_session(session.id))
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        menu.tk_popup(x, y)

    def _on_archive_session(self, session_id: str, archived: bool) -> None:
        self.controller.archive_session(session_id, archived)
        self._refresh_saved_sessions()

    def _on_delete_session(self, session_id: str) -> None:
        self.controller.delete_session(session_id)
        self._refresh_saved_sessions()
        if self.controller.mode is ChatMode.NONE:
            self._render_messages([])
            self._mode_label.configure(text="No chat open")

    # -- Chat actions -----------------------------------------------------

    def _on_new_saved_chat(self) -> None:
        if self._selected_model is None:
            messagebox.showerror("OfflineLLM", "Select a model first.")
            return
        self._run_async(
            lambda: self.controller.start_new_saved_chat(self._selected_model),
            on_done=lambda _session: self._on_chat_opened(ChatMode.SAVED),
        )

    def _on_new_offline_chat(self) -> None:
        if self._selected_model is None:
            messagebox.showerror("OfflineLLM", "Select a model first.")
            return
        self._run_async(
            lambda: self.controller.start_new_offline_chat(self._selected_model),
            on_done=lambda _result: self._on_chat_opened(ChatMode.OFFLINE),
        )

    def _on_open_saved_chat(self, session_id: str) -> None:
        self._run_async(
            lambda: self.controller.open_saved_chat(session_id),
            on_done=lambda session: self._on_chat_opened(ChatMode.SAVED, session),
        )

    def _on_chat_opened(self, mode: ChatMode, session: ChatSession | None = None) -> None:
        if mode is ChatMode.OFFLINE:
            self._mode_label.configure(text="Offline chat (no trace — closes when you leave)")
            self._render_messages([])
        else:
            self._mode_label.configure(text="Saved chat")
            self._render_messages(session.messages if session else [])
        self._refresh_saved_sessions()

    def _on_send(self) -> None:
        text = self._message_input.get().strip()
        if not text or self.controller.mode is ChatMode.NONE:
            return

        self._message_input.delete(0, "end")
        self._append_line(f"You: {text}")
        self._append_line("Assistant: ", newline=False)

        self._send_button.configure(state="disabled")

        def worker():
            try:
                for chunk in self.controller.send_message(text):
                    self.after(0, lambda c=chunk: self._append_text(c))
                self.after(0, self._on_send_complete)
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                self.after(0, lambda: self._on_send_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_send_complete(self) -> None:
        self._append_text("\n\n")
        self._send_button.configure(state="normal")
        self._refresh_saved_sessions()

    def _on_send_error(self, exc: Exception) -> None:
        self._send_button.configure(state="normal")
        messagebox.showerror("OfflineLLM", str(exc))

    def _on_download_models(self) -> None:
        dialog = DownloadModelsDialog(self, self.controller, on_downloaded=self._refresh_models)
        dialog.grab_set()

    # -- Message rendering -----------------------------------------------------

    def _render_messages(self, messages) -> None:
        self._messages_box.configure(state="normal")
        self._messages_box.delete("1.0", "end")
        for message in messages:
            prefix = "You: " if message.role.value == "user" else "Assistant: "
            self._messages_box.insert("end", f"{prefix}{message.content}\n\n")
        self._messages_box.configure(state="disabled")

    def _append_line(self, text: str, newline: bool = True) -> None:
        self._append_text(text + ("\n" if newline else ""))

    def _append_text(self, text: str) -> None:
        self._messages_box.configure(state="normal")
        self._messages_box.insert("end", text)
        self._messages_box.see("end")
        self._messages_box.configure(state="disabled")

    # -- Async helper -----------------------------------------------------

    def _run_async(self, fn, on_done=None, on_error=None) -> None:
        def worker():
            try:
                result = fn()
                if on_done is not None:
                    self.after(0, lambda: on_done(result))
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                if on_error is not None:
                    self.after(0, lambda: on_error(exc))
                else:
                    self.after(0, lambda: messagebox.showerror("OfflineLLM", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    # -- Shutdown -----------------------------------------------------

    def _on_close(self) -> None:
        # Closing the app must tear down any offline session so nothing lingers.
        self.controller.shutdown()
        self.destroy()
