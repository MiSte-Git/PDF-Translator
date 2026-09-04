"""tkinter GUI for the bootstrapper wizard.

Thin widget layer over bootstrap/controller.py::BootstrapController, which
holds all the actual state and logic (see that module's docstring for why
the split exists - in short, so the logic can be unit-tested without a
display). This module is intentionally not unit-tested directly; its
correctness is instead checked by the per-OS PyInstaller build in
.github/workflows/build-bootstrap.yml actually running the frozen
executable's `--version`/import smoke check on each of the three
platforms.

Long-running work (the GPU check subprocess call, and above all the
install itself - venv creation, pip installs, a network download) runs on
a background thread so the window stays responsive; results are handed
back to the main thread via a queue.Queue polled with Tk's own
`after()`, which is the standard safe way to touch tkinter widgets from
outside the main thread (tkinter itself is not thread-safe).
"""
from __future__ import annotations

import platform
import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from bootstrap.controller import BootstrapController
from bootstrap.installer import InstallMode, InstallProgress, InstallStep

_WINDOW_SIZE = "640x480"

# bootstrap.install_step_* i18n keys, keyed by InstallStep - see
# ui/i18n_data.py's "Geführter Bootstrapper" block.
_INSTALL_STEP_KEYS = {
    InstallStep.SOURCE: "bootstrap.install_step_source",
    InstallStep.VENV: "bootstrap.install_step_venv",
    InstallStep.DEPS: "bootstrap.install_step_deps",
    InstallStep.SHORTCUT: "bootstrap.install_step_shortcut",
}


class BootstrapApp(tk.Tk):
    def __init__(self, controller: BootstrapController | None = None) -> None:
        super().__init__()
        self.controller = controller if controller is not None else BootstrapController()
        self.geometry(_WINDOW_SIZE)
        self.title(self.controller.text("bootstrap.window_title"))

        self._container = ttk.Frame(self, padding=16)
        self._container.pack(fill="both", expand=True)
        self._current_frame: ttk.Frame | None = None

        self._selected_providers: dict[str, tk.BooleanVar] = {}
        self._provider_queue: list[str] = []

        self._show_welcome()

    # --- frame helpers -----------------------------------------------------

    def _set_frame(self, build: Callable[[ttk.Frame], None]) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
        frame = ttk.Frame(self._container)
        frame.pack(fill="both", expand=True)
        self._current_frame = frame
        build(frame)

    def _nav_row(self, frame: ttk.Frame, back: Callable[[], None] | None, next_: Callable[[], None] | None, next_label: str | None = None) -> None:
        row = ttk.Frame(frame)
        row.pack(side="bottom", fill="x", pady=(16, 0))
        if back is not None:
            ttk.Button(row, text=self.controller.text("bootstrap.back_button"), command=back).pack(side="left")
        if next_ is not None:
            label = next_label if next_label is not None else self.controller.text("bootstrap.next_button")
            ttk.Button(row, text=label, command=next_).pack(side="right")

    # --- step 1: welcome / language ----------------------------------------

    def _show_welcome(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.welcome_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(frame, text=self.controller.text("bootstrap.welcome_text"), wraplength=560, justify="left").pack(
                anchor="w", pady=(8, 16)
            )

            lang_row = ttk.Frame(frame)
            lang_row.pack(anchor="w")
            ttk.Label(lang_row, text=self.controller.text("bootstrap.language_label") + ":").pack(side="left")
            lang_var = tk.StringVar(value=self.controller.language)

            def on_language_change(*_args: object) -> None:
                self.controller.set_language(lang_var.get())
                self._show_welcome()  # rebuild so every label re-renders in the new language

            combo = ttk.Combobox(lang_row, textvariable=lang_var, values=["de", "en"], state="readonly", width=6)
            combo.pack(side="left", padx=(8, 0))
            combo.bind("<<ComboboxSelected>>", on_language_change)

            self._nav_row(frame, back=None, next_=self._show_mode)

        self._set_frame(build)

    # --- step 2: online / local ---------------------------------------------

    def _show_mode(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.mode_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(frame, text=self.controller.text("bootstrap.mode_intro"), wraplength=560, justify="left").pack(
                anchor="w", pady=(8, 16)
            )

            # Decision 3 (project doc, 01.09.2026): "Lokal" is NVIDIA/CUDA-
            # only in this first version and is not offered on macOS at
            # all - the user is steered straight to "Online" there, rather
            # than being allowed to pick Local and only finding out on the
            # next screen. LaMa/PaddleOCR on Apple Silicon (MPS) is
            # untested and out of scope for v1.
            is_mac = platform.system() == "Darwin"
            mode_var = tk.StringVar(
                value=(InstallMode.ONLINE.value if is_mac else (self.controller.mode.value if self.controller.mode else InstallMode.ONLINE.value))
            )

            online_frame = ttk.Frame(frame)
            online_frame.pack(anchor="w", fill="x", pady=(0, 12))
            ttk.Radiobutton(
                online_frame, text=self.controller.text("bootstrap.mode_online_label"), variable=mode_var, value=InstallMode.ONLINE.value
            ).pack(anchor="w")
            ttk.Label(online_frame, text=self.controller.text("bootstrap.mode_online_desc"), wraplength=560, justify="left").pack(
                anchor="w", padx=(24, 0)
            )

            local_frame = ttk.Frame(frame)
            local_frame.pack(anchor="w", fill="x")
            ttk.Radiobutton(
                local_frame,
                text=self.controller.text("bootstrap.mode_local_label"),
                variable=mode_var,
                value=InstallMode.LOCAL.value,
                state="disabled" if is_mac else "normal",
            ).pack(anchor="w")
            local_desc_key = "bootstrap.gpu_mac_unsupported" if is_mac else "bootstrap.mode_local_desc"
            ttk.Label(local_frame, text=self.controller.text(local_desc_key), wraplength=560, justify="left").pack(
                anchor="w", padx=(24, 0)
            )

            def on_next() -> None:
                self.controller.set_mode(InstallMode(mode_var.get()))
                if self.controller.mode is InstallMode.LOCAL:
                    self._show_gpu_check()
                else:
                    self._show_install()

            self._nav_row(frame, back=self._show_welcome, next_=on_next)

        self._set_frame(build)

    # --- step 3: GPU check (LOCAL mode only) --------------------------------

    def _show_gpu_check(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.mode_local_label"), font=("", 16, "bold")).pack(anchor="w")
            status_var = tk.StringVar(value=self.controller.text("bootstrap.gpu_checking"))
            ttk.Label(frame, textvariable=status_var, wraplength=560, justify="left").pack(anchor="w", pady=(8, 16))

            button_row = ttk.Frame(frame)

            def show_result() -> None:
                if platform.system() == "Darwin":
                    status_var.set(self.controller.text("bootstrap.gpu_mac_unsupported"))
                    self._render_gpu_buttons(button_row, ok=False, mac=True)
                    return

                gpu = self.controller.check_gpu()
                if gpu is None:
                    status_var.set(self.controller.text("bootstrap.gpu_not_found"))
                    self._render_gpu_buttons(button_row, ok=False, mac=False)
                elif not self.controller.gpu_driver_supported():
                    # 03.09.2026: driver older than CUDA 11.8 - no torch
                    # wheel we could install would see this GPU. Same
                    # buttons as "not found": Online, or Back.
                    status_var.set(
                        self.controller.text("bootstrap.gpu_driver_too_old", name=gpu.name, cuda_version=gpu.cuda_version)
                    )
                    self._render_gpu_buttons(button_row, ok=False, mac=True)
                elif self.controller.gpu_meets_recommendation():
                    status_var.set(self.controller.text("bootstrap.gpu_ok", name=gpu.name, vram_gb=gpu.vram_gb))
                    self._nav_row(frame, back=self._show_mode, next_=self._show_install)
                else:
                    from bootstrap.gpu_check import GPU_MIN_VRAM_GB

                    status_var.set(
                        self.controller.text(
                            "bootstrap.gpu_insufficient", name=gpu.name, vram_gb=gpu.vram_gb, min_gb=GPU_MIN_VRAM_GB
                        )
                    )
                    self._render_gpu_buttons(button_row, ok=False, mac=False)

            button_row.pack(side="bottom", fill="x", pady=(16, 0))
            self.after(50, show_result)

        self._set_frame(build)

    def _render_gpu_buttons(self, row: ttk.Frame, ok: bool, mac: bool) -> None:
        for child in row.winfo_children():
            child.destroy()
        ttk.Button(row, text=self.controller.text("bootstrap.back_button"), command=self._show_mode).pack(side="left")
        if not mac:
            ttk.Button(
                row, text=self.controller.text("bootstrap.gpu_continue_local_button"), command=self._show_install
            ).pack(side="right")

        def switch_online() -> None:
            self.controller.set_mode(InstallMode.ONLINE)
            self._show_install()

        ttk.Button(row, text=self.controller.text("bootstrap.gpu_switch_online_button"), command=switch_online).pack(
            side="right", padx=(0, 8) if not mac else (0, 0)
        )

    # --- step 4: install ------------------------------------------------

    def _show_install(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.install_title"), font=("", 16, "bold")).pack(anchor="w")
            status_var = tk.StringVar(value="")
            ttk.Label(frame, textvariable=status_var, wraplength=560, justify="left").pack(anchor="w", pady=(8, 16))
            progress = ttk.Progressbar(frame, mode="indeterminate")
            progress.pack(fill="x", pady=(0, 16))
            progress.start(12)

            result_queue: queue.Queue = queue.Queue()

            def on_progress(step_progress: InstallProgress) -> None:
                key = _INSTALL_STEP_KEYS[step_progress.step]
                text = self.controller.text(key, name=step_progress.detail) if step_progress.detail else self.controller.text(key)
                result_queue.put(("progress", text))

            def worker() -> None:
                try:
                    self.controller.run_install(progress_cb=on_progress)
                    self.controller.write_language_marker()
                    result_queue.put(("done", None))
                except Exception as exc:  # noqa: BLE001 - shown to the user as-is
                    result_queue.put(("error", str(exc)))

            threading.Thread(target=worker, daemon=True).start()

            def poll() -> None:
                try:
                    while True:
                        kind, payload = result_queue.get_nowait()
                        if kind == "progress":
                            status_var.set(payload)
                        elif kind == "done":
                            progress.stop()
                            if self.controller.mode is InstallMode.ONLINE:
                                self._show_credentials()
                            else:
                                self._show_finish()
                            return
                        elif kind == "error":
                            progress.stop()
                            self._show_install_failed(payload)
                            return
                except queue.Empty:
                    pass
                self.after(150, poll)

            self.after(150, poll)

        self._set_frame(build)

    def _show_install_failed(self, error_message: str) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.install_failed_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(
                frame,
                text=self.controller.text("bootstrap.install_failed", error=error_message),
                wraplength=560,
                justify="left",
            ).pack(anchor="w", pady=(8, 16))
            self._nav_row(frame, back=self._show_mode, next_=None)

        self._set_frame(build)

    # --- step 5: credentials (ONLINE mode only) -----------------------------

    def _show_credentials(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.credentials_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(frame, text=self.controller.text("bootstrap.credentials_intro"), wraplength=560, justify="left").pack(
                anchor="w", pady=(8, 16)
            )

            self._selected_providers = {}
            for provider in self.controller.list_providers():
                var = tk.BooleanVar(value=False)
                self._selected_providers[provider] = var
                label_key = f"bootstrap.credentials_provider_{provider}"
                ttk.Checkbutton(frame, text=self.controller.text(label_key), variable=var).pack(anchor="w")

            def on_continue() -> None:
                self._provider_queue = [p for p, v in self._selected_providers.items() if v.get()]
                self._show_next_credential_or_finish()

            row = ttk.Frame(frame)
            row.pack(side="bottom", fill="x", pady=(16, 0))
            ttk.Button(row, text=self.controller.text("bootstrap.credentials_skip_all_button"), command=self._show_finish).pack(
                side="left"
            )
            ttk.Button(row, text=self.controller.text("bootstrap.credentials_continue_button"), command=on_continue).pack(
                side="right"
            )

        self._set_frame(build)

    def _show_next_credential_or_finish(self) -> None:
        if not self._provider_queue:
            self._show_finish()
            return
        provider = self._provider_queue.pop(0)
        self._show_single_credential(provider)

    def _show_single_credential(self, provider: str) -> None:
        def build(frame: ttk.Frame) -> None:
            provider_label = self.controller.text(f"bootstrap.credentials_provider_{provider}")
            ttk.Label(frame, text=provider_label, font=("", 16, "bold")).pack(anchor="w")
            explain_key = f"bootstrap.credentials_explain_{provider}"
            ttk.Label(frame, text=self.controller.text(explain_key), wraplength=560, justify="left").pack(
                anchor="w", pady=(8, 16)
            )
            ttk.Button(
                frame,
                text=self.controller.text("bootstrap.credentials_open_signup_button"),
                command=lambda: self.controller.open_signup_page(provider),
            ).pack(anchor="w", pady=(0, 16))

            ttk.Label(frame, text=self.controller.text("bootstrap.credentials_key_label", provider=provider_label)).pack(
                anchor="w"
            )
            key_var = tk.StringVar(value="")
            entry = ttk.Entry(frame, textvariable=key_var, show="*", width=50)
            entry.pack(anchor="w", pady=(4, 8))
            status_var = tk.StringVar(value="")
            ttk.Label(frame, textvariable=status_var).pack(anchor="w")

            def on_save() -> None:
                value = key_var.get().strip()
                if not value:
                    return
                self.controller.save_provider_credential(provider, value)
                status_var.set(self.controller.text("bootstrap.credentials_saved"))

            ttk.Button(frame, text=self.controller.text("bootstrap.credentials_save_button"), command=on_save).pack(
                anchor="w", pady=(0, 16)
            )

            self._nav_row(
                frame,
                back=None,
                next_=self._show_next_credential_or_finish,
                next_label=self.controller.text("bootstrap.credentials_continue_button"),
            )

        self._set_frame(build)

    # --- step 6: finish ------------------------------------------------

    def _show_finish(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.finish_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(frame, text=self.controller.text("bootstrap.finish_text"), wraplength=560, justify="left").pack(
                anchor="w", pady=(8, 16)
            )

            def on_launch() -> None:
                self.controller.launch_app()
                self.destroy()

            row = ttk.Frame(frame)
            row.pack(side="bottom", fill="x", pady=(16, 0))
            ttk.Button(row, text=self.controller.text("bootstrap.finish_close_button"), command=self.destroy).pack(side="left")
            ttk.Button(row, text=self.controller.text("bootstrap.finish_launch_button"), command=on_launch).pack(side="right")

        self._set_frame(build)


def main() -> None:
    try:
        app = BootstrapApp()
        app.mainloop()
    except Exception:
        _report_startup_crash()
        raise


def _write_meipass_tcl_tk_report(f) -> None:
    """Writes what tcl86t.dll/tk86t.dll actually ended up inside THIS
    exe's own onefile bundle - not what was available at build time,
    which .github/workflows/build-bootstrap.yml's own diagnostic step
    already checked and found to be a single, correctly-versioned
    (8.6.15) DLL with no alternative candidate anywhere on that runner.
    Since the crash still happens with a real user's build despite that,
    the only way left to find the actual discrepancy is to look inside
    the exe that is actually crashing, on the machine where it actually
    crashes - this runs in the very same frozen process that just failed
    to start Tk, using sys._MEIPASS (PyInstaller's own extraction
    directory for this run, already populated by the time this code
    runs) rather than anything guessed from outside.
    """
    import os as _os
    import sys

    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        f.write("_MEIPASS: not set (not running as a frozen onefile build)\n")
        return

    f.write(f"_MEIPASS={meipass}\n")
    try:
        entries = sorted(_os.listdir(meipass))
        f.write(f"_MEIPASS top-level entries ({len(entries)}): {', '.join(entries)}\n")
    except OSError as exc:
        f.write(f"_MEIPASS listdir failed: {exc}\n")

    if sys.platform != "win32":
        return

    for dll_name in ("tcl86t.dll", "tk86t.dll"):
        dll_path = _os.path.join(meipass, dll_name)
        if not _os.path.isfile(dll_path):
            f.write(f"{dll_name}: NOT FOUND at {dll_path}\n")
            continue
        size = _os.path.getsize(dll_path)
        version = _win_file_version(dll_path)
        f.write(f"{dll_name}: path={dll_path} size={size} FileVersion={version}\n")


def _win_file_version(path: str) -> str:
    """Reads a Windows PE file's FixedFileInfo FileVersion via the plain
    Win32 version-info API (GetFileVersionInfoW/VerQueryValueW) - no
    external dependency, works the same whether or not Tk is usable.
    Returns a "MAJOR.MINOR.BUILD.REVISION" string, or a short
    "<error: ...>" placeholder if anything about the lookup fails (never
    raises - this is diagnostic best-effort, not allowed to itself crash
    the crash handler).
    """
    import ctypes
    from ctypes import wintypes

    try:
        version_dll = ctypes.windll.version
        size = version_dll.GetFileVersionInfoSizeW(path, None)
        if not size:
            return "<error: GetFileVersionInfoSizeW returned 0>"
        buf = ctypes.create_string_buffer(size)
        if not version_dll.GetFileVersionInfoW(path, 0, size, buf):
            return "<error: GetFileVersionInfoW failed>"

        class _VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD),
                ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD),
                ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD),
                ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD),
                ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD),
                ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD),
                ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD),
            ]

        value_ptr = ctypes.c_void_p()
        value_len = ctypes.c_uint()
        if not version_dll.VerQueryValueW(
            buf, "\\", ctypes.byref(value_ptr), ctypes.byref(value_len)
        ):
            return "<error: VerQueryValueW failed>"
        info = ctypes.cast(value_ptr, ctypes.POINTER(_VS_FIXEDFILEINFO)).contents
        ms, ls = info.dwFileVersionMS, info.dwFileVersionLS
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception as exc:  # noqa: BLE001 - diagnostic best-effort only
        return f"<error: {exc!r}>"


def _report_startup_crash() -> None:
    """Writes the current exception to a log file and shows it in a way
    the user can actually copy - as opposed to PyInstaller's own
    --windowed crash dialog ("Unhandled exception in script"), which a
    user hit repeatedly during Windows testing (04.09.2026, Tcl/Tk
    version-mismatch bug - see .github/workflows/build-bootstrap.yml's
    Windows smoke-test step for the CI-side half of that story) and
    could only get to us as screenshots, since that particular dialog's
    text cannot be selected or saved.

    Deliberately does not touch tkinter: the exception that lands here
    can be tkinter/Tcl itself failing during BootstrapApp.__init__'s
    very first line (super().__init__(), i.e. tk.Tk() - exactly what
    happened in practice), so any error path that itself needs a
    working Tk would just crash a second time, less informatively than
    the first. ctypes.windll.user32.MessageBoxW is a plain Win32 API
    call with no such dependency, and - unlike PyInstaller's dialog -
    its text can be selected/copied with Ctrl+C, which is standard
    behaviour for a native Windows message box.
    """
    import datetime
    import os as _os
    import platform
    import sys
    import tempfile
    import traceback

    tb = traceback.format_exc()
    log_dir = _os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    log_path = _os.path.join(log_dir, "PDF-Translator", "bootstrap-crash.log")
    log_written = False
    try:
        _os.makedirs(_os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.datetime.now().isoformat()} ---\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Platform: {platform.platform()}\n")
            for var in ("TCL_LIBRARY", "TK_LIBRARY"):
                f.write(f"{var}={_os.environ.get(var, '<not set>')}\n")
            _write_meipass_tcl_tk_report(f)
            f.write(tb)
            f.write("\n")
        log_written = True
    except OSError:
        pass

    if log_written:
        message = (
            "Der Installer konnte nicht gestartet werden.\n\n"
            f"Details wurden gespeichert unter:\n{log_path}\n\n"
            "Bitte diese Datei mitschicken, falls du das meldest.\n\n"
            "---\n\n"
            f"{tb}"
        )
    else:
        message = f"Der Installer konnte nicht gestartet werden:\n\n{tb}"

    title = "PDF-Translator Setup - Fehler beim Start / Startup Error"
    if sys.platform == "win32":
        import ctypes

        # MB_OK | MB_ICONERROR. Runs even though Tk/Tcl may be broken -
        # this is a bare Win32 API call, not a tkinter one.
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    else:
        print(f"{title}\n\n{message}", file=sys.stderr)


if __name__ == "__main__":
    main()
