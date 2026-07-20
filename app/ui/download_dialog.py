"""'Download models...' dialog: a curated list of known-good GGUF models, or
any direct .gguf URL the user pastes.
"""

from __future__ import annotations

import threading
from urllib.parse import urlparse

import customtkinter as ctk
from tkinter import messagebox

from core.model_catalog import CURATED
from core.model_download import DownloadProgress


class DownloadModelsDialog(ctk.CTkToplevel):
    def __init__(self, parent, controller, on_downloaded=None):
        super().__init__(parent)
        self.title("Download a model")
        self.geometry("560x520")
        self.resizable(False, False)

        self._controller = controller
        self._on_downloaded = on_downloaded
        self._cancel_requested = False

        ctk.CTkLabel(
            self, text="Pick one, or paste a direct .gguf URL below.", anchor="w"
        ).pack(fill="x", padx=16, pady=(16, 8))

        catalog_frame = ctk.CTkScrollableFrame(self, height=260)
        catalog_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        for entry in CURATED:
            self._add_catalog_row(catalog_frame, entry)

        ctk.CTkLabel(self, text="Custom .gguf URL", anchor="w", font=ctk.CTkFont(weight="bold")).pack(
            fill="x", padx=16
        )
        url_row = ctk.CTkFrame(self, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(4, 12))
        self._url_entry = ctk.CTkEntry(url_row, placeholder_text="https://.../model.gguf")
        self._url_entry.pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(url_row, text="Download", command=self._on_download_custom_url).pack(side="left")

        self._status_label = ctk.CTkLabel(self, text="", anchor="w")
        self._status_label.pack(fill="x", padx=16)
        self._progress_bar = ctk.CTkProgressBar(self)
        self._progress_bar.set(0)
        self._progress_bar.pack(fill="x", padx=16, pady=(4, 16))

        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _add_catalog_row(self, parent, entry) -> None:
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=4)
        row.grid_columnconfigure(0, weight=1)

        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="we", padx=8, pady=6)
        ctk.CTkLabel(text_frame, text=entry.display_name, anchor="w", font=ctk.CTkFont(weight="bold")).pack(
            fill="x"
        )
        ctk.CTkLabel(text_frame, text=entry.description, anchor="w", justify="left", wraplength=380).pack(
            fill="x"
        )

        ctk.CTkButton(
            row, text="Download", width=90,
            command=lambda e=entry: self._start_download(e.source_url, e.id + ".gguf"),
        ).grid(row=0, column=1, padx=8)

    def _on_download_custom_url(self) -> None:
        url = self._url_entry.get().strip()
        if not url:
            return
        name = urlparse(url).path.rsplit("/", 1)[-1] or "model"
        self._start_download(url, name)

    def _start_download(self, url: str, file_name: str) -> None:
        self._cancel_requested = False
        self._status_label.configure(text=f"Starting download of {file_name}...")
        self._progress_bar.set(0)

        def on_progress(progress: DownloadProgress) -> None:
            fraction = progress.fraction_complete
            self.after(0, lambda: self._update_progress(progress, fraction))

        def worker():
            try:
                self._controller.download_model(
                    url, file_name, on_progress=on_progress,
                    should_cancel=lambda: self._cancel_requested,
                )
                self.after(0, self._on_download_done)
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                self.after(0, lambda: self._on_download_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, progress: DownloadProgress, fraction: float | None) -> None:
        if fraction is not None:
            self._progress_bar.set(fraction)
            mb_received = progress.bytes_received / 1024 / 1024
            mb_total = progress.total_bytes / 1024 / 1024
            self._status_label.configure(text=f"{mb_received:.0f} MB / {mb_total:.0f} MB")
        else:
            mb_received = progress.bytes_received / 1024 / 1024
            self._status_label.configure(text=f"{mb_received:.0f} MB downloaded")

    def _on_download_done(self) -> None:
        self._status_label.configure(text="Done.")
        self._progress_bar.set(1)
        if self._on_downloaded is not None:
            self._on_downloaded()

    def _on_download_error(self, exc: Exception) -> None:
        self._status_label.configure(text="Failed.")
        messagebox.showerror("Download failed", str(exc))

    def _on_window_close(self) -> None:
        self._cancel_requested = True
        self.destroy()
