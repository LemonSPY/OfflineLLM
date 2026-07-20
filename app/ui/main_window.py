"""Main application window: a minimal, centered chat UI (collapsible sidebar,
centered logo empty-state, bottom input pill) modeled on common local-LLM
chat clients.

Network/process calls (starting llama-server, streaming completions) block,
so they always run on a background thread; results are marshalled back to
the Tkinter main thread via `self.after(0, ...)`, which is the only
thread-safe way to touch Tkinter/CustomTkinter widgets.
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from core.app_controller import AppController, ChatMode
from core.chat_models import ChatSession, ChatSessionStatus
from core.model_manager import ModelInfo

from .download_dialog import DownloadModelsDialog

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OfflineLLM")
        self.geometry("1100x720")
        self.configure(fg_color="white")

        self.controller = AppController()
        self._show_archived = tk.BooleanVar(value=False)
        self._selected_model: ModelInfo | None = None
        self._sidebar_visible = False

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_layout()
        self._refresh_models()
        self._refresh_saved_sessions()

    # -- Layout -----------------------------------------------------

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_sidebar()
        self._build_main_area()

    def _build_top_bar(self) -> None:
        top_bar = ctk.CTkFrame(self, fg_color="white", height=52, corner_radius=0)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="we")
        top_bar.grid_propagate(False)

        icon_font = ctk.CTkFont(size=17)
        ctk.CTkButton(
            top_bar, text="☰", width=36, height=36, corner_radius=8, font=icon_font,
            fg_color="transparent", text_color="black", hover_color="#eeeeee",
            command=self._on_toggle_sidebar,
        ).place(x=12, y=8)
        ctk.CTkButton(
            top_bar, text="✎", width=36, height=36, corner_radius=8, font=icon_font,
            fg_color="transparent", text_color="black", hover_color="#eeeeee",
            command=self._on_new_saved_chat,
        ).place(x=52, y=8)

        self._mode_label = ctk.CTkLabel(
            top_bar, text="", font=ctk.CTkFont(size=13), text_color="#666666",
        )
        self._mode_label.place(relx=1.0, x=-16, y=16, anchor="ne")

    def _build_sidebar(self) -> None:
        self._sidebar = ctk.CTkFrame(self, width=280, fg_color="#f7f7f7", corner_radius=0)
        self._sidebar.grid_rowconfigure(1, weight=1)
        self._sidebar.grid_propagate(False)
        # Hidden by default (matches the reference layout, which shows only
        # the top-bar icons until the sidebar is explicitly opened).

        ctk.CTkLabel(self._sidebar, text="Chats", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )

        self._sessions_frame = ctk.CTkScrollableFrame(self._sidebar, fg_color="transparent")
        self._sessions_frame.grid(row=1, column=0, padx=8, pady=4, sticky="nswe")

        ctk.CTkCheckBox(
            self._sidebar, text="Show archived", variable=self._show_archived,
            command=self._refresh_saved_sessions,
        ).grid(row=2, column=0, padx=16, pady=(4, 16), sticky="w")

    def _on_toggle_sidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_visible:
            self._sidebar.grid(row=1, column=0, sticky="nswe")
        else:
            self._sidebar.grid_remove()

    def _build_main_area(self) -> None:
        main_area = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        main_area.grid(row=1, column=1, sticky="nswe")
        main_area.grid_columnconfigure(0, weight=1)
        main_area.grid_rowconfigure(0, weight=1)

        # Empty-state placeholder: the app's logo, centered - shown until the
        # first message of a chat exists, then swapped for the messages box.
        self._empty_state_frame = ctk.CTkFrame(main_area, fg_color="white")
        logo_path = os.path.join(_ASSETS_DIR, "logo.png")
        if os.path.isfile(logo_path):
            logo_image = Image.open(logo_path)
            w, h = logo_image.size
            display_w = 160
            display_h = int(display_w * h / w)
            ctk.CTkLabel(
                self._empty_state_frame, text="",
                image=ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(display_w, display_h)),
            ).pack(expand=True)
        self._empty_state_frame.grid(row=0, column=0, sticky="nswe")

        self._messages_box = ctk.CTkTextbox(
            main_area, wrap="word", state="disabled", fg_color="white", border_width=0,
            font=ctk.CTkFont(size=14),
        )
        # Not gridded yet - shown once there's something to display.

        self._build_input_pill(main_area)

    def _build_input_pill(self, main_area: ctk.CTkFrame) -> None:
        # A wrapper row centers a fixed-width pill (rather than letting it
        # span edge-to-edge), matching the reference layout.
        wrapper = ctk.CTkFrame(main_area, fg_color="white")
        wrapper.grid(row=1, column=0, sticky="we", pady=(0, 28))
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_columnconfigure(2, weight=1)

        pill = ctk.CTkFrame(wrapper, fg_color="#f2f2f2", corner_radius=26, height=56)
        pill.grid(row=0, column=1)
        pill.grid_propagate(False)
        pill.configure(width=760)

        icon_font = ctk.CTkFont(size=15)

        self._message_input = ctk.CTkEntry(
            pill, placeholder_text="Send a message", border_width=0, fg_color="transparent",
            font=ctk.CTkFont(size=14), width=470, height=30,
        )
        self._message_input.place(x=20, y=13)
        self._message_input.bind("<Return>", lambda _e: self._on_send())

        ctk.CTkButton(
            pill, text="+", width=32, height=32, corner_radius=16, font=icon_font,
            fg_color="white", text_color="black", hover_color="#e2e2e2",
            command=self._on_download_models,
        ).place(relx=1.0, x=-220, y=12, anchor="nw")

        self._offline_button = ctk.CTkButton(
            pill, text="\U0001F310", width=32, height=32, corner_radius=16, font=icon_font,
            fg_color="white", text_color="black", hover_color="#e2e2e2",
            command=self._on_new_offline_chat,
        )
        self._offline_button.place(relx=1.0, x=-178, y=12, anchor="nw")

        self._model_picker = ctk.CTkOptionMenu(
            pill, values=["No models found"], command=self._on_model_selected,
            width=130, height=32, corner_radius=16, font=ctk.CTkFont(size=12),
            fg_color="white", text_color="black", button_color="#e2e2e2", button_hover_color="#d5d5d5",
            dropdown_fg_color="white",
        )
        self._model_picker.place(relx=1.0, x=-138, y=12, anchor="nw")

        self._send_button = ctk.CTkButton(
            pill, text="↑", width=36, height=36, corner_radius=18, font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#d0d0d0", text_color="black", hover_color="#b8b8b8",
            command=self._on_send,
        )
        self._send_button.place(relx=1.0, x=-46, y=10, anchor="nw")

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

        menu_button = ctk.CTkButton(row, text="⋮", width=28, fg_color="transparent", text_color="black",
                                     hover_color="#e2e2e2", command=lambda: self._show_session_menu(session))
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
            self._mode_label.configure(text="")

    # -- Chat actions -----------------------------------------------------

    def _on_new_saved_chat(self) -> None:
        if self._selected_model is None:
            messagebox.showerror("OfflineLLM", "Download a model first.")
            return
        self._mode_label.configure(text="Starting model server...")
        self._run_async(
            lambda: self.controller.start_new_saved_chat(self._selected_model),
            on_done=lambda _session: self._on_chat_opened(ChatMode.SAVED),
            on_error=self._on_start_chat_error,
        )

    def _on_new_offline_chat(self) -> None:
        if self._selected_model is None:
            messagebox.showerror("OfflineLLM", "Download a model first.")
            return
        self._mode_label.configure(text="Starting model server...")
        self._run_async(
            lambda: self.controller.start_new_offline_chat(self._selected_model),
            on_done=lambda _result: self._on_chat_opened(ChatMode.OFFLINE),
            on_error=self._on_start_chat_error,
        )

    def _on_start_chat_error(self, exc: Exception) -> None:
        self._mode_label.configure(text="")
        messagebox.showerror("OfflineLLM", str(exc))

    def _on_open_saved_chat(self, session_id: str) -> None:
        self._run_async(
            lambda: self.controller.open_saved_chat(session_id),
            on_done=lambda session: self._on_chat_opened(ChatMode.SAVED, session),
        )

    def _on_chat_opened(self, mode: ChatMode, session: ChatSession | None = None) -> None:
        if mode is ChatMode.OFFLINE:
            self._mode_label.configure(text="Offline chat — no trace, closes when you leave")
            self._render_messages([])
        else:
            self._mode_label.configure(text="Saved chat")
            self._render_messages(session.messages if session else [])
        self._refresh_saved_sessions()

    def _on_send(self) -> None:
        text = self._message_input.get().strip()
        if not text:
            return

        if self.controller.mode is ChatMode.NONE:
            messagebox.showerror("OfflineLLM", "Start a saved or offline chat first (✎ or \U0001F310 above).")
            return

        self._message_input.delete(0, "end")
        self._show_messages_box()
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

    def _show_messages_box(self) -> None:
        self._empty_state_frame.grid_remove()
        self._messages_box.grid(row=0, column=0, sticky="nswe", padx=40, pady=(16, 0))

    def _show_empty_state(self) -> None:
        self._messages_box.grid_remove()
        self._empty_state_frame.grid(row=0, column=0, sticky="nswe")

    def _render_messages(self, messages) -> None:
        if not messages:
            self._show_empty_state()
            return

        self._show_messages_box()
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
