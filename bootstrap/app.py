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
from tkinter import messagebox, ttk
from typing import Callable

from bootstrap.controller import BootstrapController
from bootstrap.installer import InstallMode, InstallProgress, InstallStep
from ui.i18n_data import LOCALES

_WINDOW_SIZE = "500x440"
# 07.09.2026: shrunk from 560x440 to 500x380 ("noch kleiner und
# moderner"), then grown back to 500x440 the same day to make room
# for the persistent "Abbrechen" bar added in __init__ (see
# BootstrapApp.__init__ and _set_frame) - every screen needs it, not
# just one, so it could not be folded into an existing per-screen
# button row without touching every _show_*/_render_* builder
# separately. Net effect vs. the original 560x480 is still a real
# reduction (about 30% less area), just not as small as the brief
# 500x380 in between.
_TEXT_WRAP = 440

# bootstrap.finish_* only - see _show_finish(): far less content than
# every other screen (one line of text, two buttons, no Abbrechen bar
# - see _set_frame(..., show_cancel=False)), so the shared
# _WINDOW_SIZE above would leave a lot of visibly empty space.
_FINISH_WINDOW_SIZE = "500x230"

# bootstrap.install_step_* i18n keys, keyed by InstallStep - see
# ui/i18n_data.py's "Geführter Bootstrapper" block.
_INSTALL_STEP_KEYS = {
    InstallStep.SOURCE: "bootstrap.install_step_source",
    InstallStep.VENV: "bootstrap.install_step_venv",
    InstallStep.DEPS: "bootstrap.install_step_deps",
    InstallStep.SHORTCUT: "bootstrap.install_step_shortcut",
}


class _Tooltip:
    """Lightweight hover tooltip for a single tk/ttk widget.

    07.09.2026 (Michael: "Ausserdem haette ich noch gerne zu jeder Option
    in der App eine klare Nutzerfreundliche Tooltip und eine Hilfe. So
    das automatisch zu jedem Button, Option usw. auch ein richtiger
    Hilfetext existiert."): tkinter has no built-in equivalent to Qt's
    setToolTip()/setWhatsThis() (see ui/app.py's MainWindow._help_widgets/
    SettingsDialog._settings_help_widgets/HardwareCheckDialog.
    _hw_check_help_widgets for that side), and this wizard has neither a
    menu bar to hang a "Direkthilfe"/WhatsThis-mode entry on nor a second
    interaction model beyond hovering - so the short tooltip and the
    longer explanation are combined into ONE popup per widget (see the
    "bootstrap.help.*" i18n keys: a blank line separates the short cue
    from the longer paragraph) rather than two separate mechanisms.

    Re-created fresh every time a screen is built (see BootstrapApp._set_
    frame - each _show_*() tears down the previous frame's widgets
    entirely and builds new ones), so there is no retranslate() to wire
    up here unlike the Qt app: the tooltip text is simply read via
    self.controller.text(...) at the point the widget is created, already
    in whatever language is current then.
    """

    _DELAY_MS = 500
    _WRAP_LENGTH = 360

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self._after_id: str | None = None
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, _event: object = None) -> None:
        self._cancel_scheduled()
        self._after_id = self.widget.after(self._DELAY_MS, self._show)

    def _cancel_scheduled(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self) -> None:
        if self._tip is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        except Exception:
            return
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        try:
            self._tip.wm_attributes("-topmost", True)
        except Exception:
            pass
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._tip,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            wraplength=self._WRAP_LENGTH,
            padx=6,
            pady=4,
        ).pack()

    def _hide(self, _event: object = None) -> None:
        self._cancel_scheduled()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


def _tip(widget: tk.Widget, text: str) -> None:
    """Attaches a hover tooltip to `widget` - short helper so call sites
    below read as a one-liner (`_tip(button, self.controller.text(...))`)
    rather than needing to hold on to the _Tooltip instance themselves
    (nothing after construction is ever called on it again - see
    _Tooltip's own docstring on why there is no retranslate() path)."""
    _Tooltip(widget, text)


class BootstrapApp(tk.Tk):
    def __init__(self, controller: BootstrapController | None = None) -> None:
        super().__init__()
        self.controller = controller if controller is not None else BootstrapController()
        self.geometry(_WINDOW_SIZE)
        # 06.09.2026 ("können wir jetzt kleiner und hübscher machen"): a
        # fixed-size wizard window is the normal convention for an
        # installer - not resizable also means no layout ever has to cope
        # with extra empty space or a squeezed wraplength.
        self.resizable(False, False)
        self.title(self.controller.text("bootstrap.window_title"))

        # 07.09.2026: default ttk button/checkbox padding is quite tight
        # (a few pixels), which reads as cramped rather than "modern" -
        # especially now that the window itself is smaller. This only
        # widens click targets and breathing room; it deliberately does
        # NOT switch ttk themes (e.g. to "clam"), which would fight the
        # OS's own native widget rendering on Windows/macOS rather than
        # complement it.
        style = ttk.Style(self)
        style.configure("TButton", padding=(14, 8))
        style.configure("TCheckbutton", padding=(0, 5))
        style.configure("TRadiobutton", padding=(0, 5))

        self._installing = False
        # 07.09.2026 ("fehlt uns nicht auch ein Abbrechen Button
        # ueberall"): a persistent bar OUTSIDE the per-screen frame
        # that _set_frame() swaps out, rather than adding a Cancel
        # button to every individual _show_*/_render_* button row -
        # there are five different ones, including one
        # (_show_install's progress screen) that had no button row at
        # all before this. Packed (side="bottom") BEFORE
        # self._container below, so it reserves its own space first
        # and _container gets the remaining area - the standard Tk
        # pack ordering for a fixed footer; re-packing it later
        # (_set_frame) does not change this ordering, only whether it
        # is shown at all. Hidden only for the finish screen - once
        # install has succeeded there is nothing left to cancel.
        self._cancel_bar = ttk.Frame(self, padding=(16, 8))
        self._cancel_bar.pack(side="bottom", fill="x")
        cancel_button = ttk.Button(
            self._cancel_bar, text=self.controller.text("bootstrap.cancel_button"), command=self._on_cancel
        )
        cancel_button.pack(side="left")
        _tip(cancel_button, self.controller.text("bootstrap.help.cancel_button"))

        self._container = ttk.Frame(self, padding=16)
        self._container.pack(fill="both", expand=True)
        self._current_frame: ttk.Frame | None = None

        self._selected_providers: dict[str, tk.BooleanVar] = {}
        # 07.09.2026: replaced a pop-from-a-queue design
        # (self._provider_queue) with a fixed list + index - a queue
        # has no way to go back to an already-shown provider, which is
        # exactly the missing "Zurueck" button reported on this screen.
        self._credential_providers: list[str] = []
        self._credential_index: int = 0

        self._show_welcome()

    def _on_cancel(self) -> None:
        """Closes the wizard after confirmation - the whole install
        (or just the wizard itself, before or after installing) is
        abandoned. Does not attempt to clean up any partial
        install_root() state left behind (see the stronger
        confirmation text shown while an install is running) -
        re-running the setup afterwards overwrites/completes it the
        same way a second normal run always could.
        """
        key = "bootstrap.cancel_confirm_installing" if self._installing else "bootstrap.cancel_confirm"
        if messagebox.askyesno(self.controller.text("bootstrap.cancel_title"), self.controller.text(key)):
            self.destroy()

    def report_callback_exception(self, exc, val, tb) -> None:
        """Overrides tkinter's own hook for exceptions raised inside a
        widget callback (a button command, an .after() poll, ...) - by
        default tkinter just prints these to stderr and carries on, which
        in a --windowed build (no console, stderr goes nowhere) means the
        callback silently does nothing and whatever screen it was
        supposed to finish building is left half-drawn, with no error
        visible anywhere. 04.09.2026: exactly this happened on a real
        install - the credentials screen's checkboxes+buttons never
        appeared after an exception partway through _show_credentials'
        build(), leaving only its title and intro text with no way
        forward except closing the window. Routing these through the
        same _report_startup_crash() used for a startup failure at least
        gets a real traceback into bootstrap-crash.log and in front of
        the user instead of vanishing.
        """
        import traceback

        formatted = "".join(traceback.format_exception(exc, val, tb))
        _report_startup_crash(formatted)

    # --- frame helpers -----------------------------------------------------

    def _set_frame(
        self, build: Callable[[ttk.Frame], None], *, window_size: str = _WINDOW_SIZE, show_cancel: bool = True
    ) -> None:
        self.geometry(window_size)
        if show_cancel:
            self._cancel_bar.pack(side="bottom", fill="x")
        else:
            self._cancel_bar.pack_forget()
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
            back_button = ttk.Button(row, text=self.controller.text("bootstrap.back_button"), command=back)
            back_button.pack(side="left")
            _tip(back_button, self.controller.text("bootstrap.help.back_button"))
        if next_ is not None:
            label = next_label if next_label is not None else self.controller.text("bootstrap.next_button")
            next_button = ttk.Button(row, text=label, command=next_)
            next_button.pack(side="right")
            _tip(next_button, self.controller.text("bootstrap.help.next_button"))

    # --- step 1: welcome / language ----------------------------------------

    def _show_welcome(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.welcome_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(frame, text=self.controller.text("bootstrap.welcome_text"), wraplength=_TEXT_WRAP, justify="left").pack(
                anchor="w", pady=(8, 16)
            )

            # 07.09.2026 ("Sprachenleiste ist immer noch nicht mittig"):
            # anchor="center" alone (06.09.2026's fix) turned out not to
            # be reliably enough - packing lang_row itself with
            # anchor="center" only centers it WITHIN whatever parcel
            # width it happens to get, and nothing here forced that
            # parcel to actually span the full window width. Forcing it
            # explicitly with an outer fill="x" row and an inner frame
            # (plain pack(), whose own default anchor is already
            # "center") holding the actual label+combobox is the
            # standard, unambiguous way to center a small fixed-size
            # group of widgets: the outer frame's width is no longer in
            # question (fill="x" guarantees it spans the parent), only
            # the inner one's position within it is being centered.
            lang_row = ttk.Frame(frame)
            lang_row.pack(fill="x")
            lang_inner = ttk.Frame(lang_row)
            lang_inner.pack()
            ttk.Label(lang_inner, text=self.controller.text("bootstrap.language_label") + ":").pack(side="left")

            # 06.09.2026 ("alle Sprachen sollten beim Installer verfuegbar
            # sein"): this used to hardcode values=["de", "en"], left over
            # from before ui/i18n_data.py grew to 9 locales. LOCALES (the
            # same Qt-free source ui/app.py's own language switcher and
            # bootstrap/controller.py's CATALOGUES import already use) is
            # the single place that list is defined - reading it here
            # means a tenth language added there needs no change in this
            # file. The combobox shows each language's own native_name
            # (Deutsch, English, Français, ...) rather than raw codes, so
            # a name_to_code lookup translates the selection back.
            name_to_code = {loc.native_name: loc.code for loc in LOCALES}
            code_to_name = {loc.code: loc.native_name for loc in LOCALES}
            lang_var = tk.StringVar(value=code_to_name.get(self.controller.language, self.controller.language))

            def on_language_change(*_args: object) -> None:
                code = name_to_code.get(lang_var.get())
                if code is not None:
                    self.controller.set_language(code)
                self._show_welcome()  # rebuild so every label re-renders in the new language

            combo = ttk.Combobox(
                lang_inner,
                textvariable=lang_var,
                values=[loc.native_name for loc in LOCALES],
                state="readonly",
                width=13,
            )
            combo.pack(side="left", padx=(8, 0))
            combo.bind("<<ComboboxSelected>>", on_language_change)
            _tip(combo, self.controller.text("bootstrap.help.language_combo"))

            self._nav_row(frame, back=None, next_=self._show_mode)

        self._set_frame(build)

    # --- step 2: online / local ---------------------------------------------

    def _show_mode(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.mode_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(frame, text=self.controller.text("bootstrap.mode_intro"), wraplength=_TEXT_WRAP, justify="left").pack(
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
            online_radio = ttk.Radiobutton(
                online_frame, text=self.controller.text("bootstrap.mode_online_label"), variable=mode_var, value=InstallMode.ONLINE.value
            )
            online_radio.pack(anchor="w")
            _tip(online_radio, self.controller.text("bootstrap.help.mode_online_radio"))
            ttk.Label(online_frame, text=self.controller.text("bootstrap.mode_online_desc"), wraplength=_TEXT_WRAP, justify="left").pack(
                anchor="w", padx=(24, 0)
            )

            local_frame = ttk.Frame(frame)
            local_frame.pack(anchor="w", fill="x")
            local_radio = ttk.Radiobutton(
                local_frame,
                text=self.controller.text("bootstrap.mode_local_label"),
                variable=mode_var,
                value=InstallMode.LOCAL.value,
                state="disabled" if is_mac else "normal",
            )
            local_radio.pack(anchor="w")
            _tip(local_radio, self.controller.text("bootstrap.help.mode_local_radio"))
            local_desc_key = "bootstrap.gpu_mac_unsupported" if is_mac else "bootstrap.mode_local_desc"
            ttk.Label(local_frame, text=self.controller.text(local_desc_key), wraplength=_TEXT_WRAP, justify="left").pack(
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
            ttk.Label(frame, textvariable=status_var, wraplength=_TEXT_WRAP, justify="left").pack(anchor="w", pady=(8, 16))

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
        gpu_back_button = ttk.Button(row, text=self.controller.text("bootstrap.back_button"), command=self._show_mode)
        gpu_back_button.pack(side="left")
        _tip(gpu_back_button, self.controller.text("bootstrap.help.back_button"))
        if not mac:
            continue_local_button = ttk.Button(
                row, text=self.controller.text("bootstrap.gpu_continue_local_button"), command=self._show_install
            )
            continue_local_button.pack(side="right")
            _tip(continue_local_button, self.controller.text("bootstrap.help.gpu_continue_local_button"))

        def switch_online() -> None:
            self.controller.set_mode(InstallMode.ONLINE)
            self._show_install()

        switch_online_button = ttk.Button(
            row, text=self.controller.text("bootstrap.gpu_switch_online_button"), command=switch_online
        )
        switch_online_button.pack(side="right", padx=(0, 8) if not mac else (0, 0))
        _tip(switch_online_button, self.controller.text("bootstrap.help.gpu_switch_online_button"))

    # --- step 4: install ------------------------------------------------

    def _show_install(self) -> None:
        self._installing = True

        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.install_title"), font=("", 16, "bold")).pack(anchor="w")
            status_var = tk.StringVar(value="")
            ttk.Label(frame, textvariable=status_var, wraplength=_TEXT_WRAP, justify="left").pack(anchor="w", pady=(8, 16))
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
                            self._installing = False
                            if self.controller.mode is InstallMode.ONLINE:
                                self._show_credentials()
                            else:
                                self._show_finish()
                            return
                        elif kind == "error":
                            progress.stop()
                            self._installing = False
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
                wraplength=_TEXT_WRAP,
                justify="left",
            ).pack(anchor="w", pady=(8, 16))
            self._nav_row(frame, back=self._show_mode, next_=None)

        self._set_frame(build)

    # --- step 5: credentials (ONLINE mode only) -----------------------------

    def _show_credentials(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.credentials_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(frame, text=self.controller.text("bootstrap.credentials_intro"), wraplength=_TEXT_WRAP, justify="left").pack(
                anchor="w", pady=(8, 16)
            )

            self._selected_providers = {}

            # 06.09.2026: "Weiter" used to be always enabled, so clicking
            # it with nothing checked silently behaved exactly like "Später
            # in den Einstellungen" - not wrong, just confusing (a real
            # user asked whether that was intentional). Disabling it until
            # at least one provider is checked makes the two buttons'
            # difference visible instead of only discoverable by clicking.
            def update_continue_state() -> None:
                any_selected = any(v.get() for v in self._selected_providers.values())
                continue_button.state(["!disabled"] if any_selected else ["disabled"])

            for provider in self.controller.list_providers():
                # 07.09.2026: pre-check providers already chosen on a
                # previous visit to this screen - without this, using
                # the new "Zurueck" button from a single-credential
                # screen back to this one would silently un-check
                # everything the user had already picked.
                var = tk.BooleanVar(value=provider in self._credential_providers)
                self._selected_providers[provider] = var
                label_key = f"bootstrap.credentials_provider_{provider}"
                provider_label = self.controller.text(label_key)
                checkbox = ttk.Checkbutton(
                    frame,
                    text=provider_label,
                    variable=var,
                    command=update_continue_state,
                )
                checkbox.pack(anchor="w")
                _tip(checkbox, self.controller.text("bootstrap.help.credentials_checkbox", provider=provider_label))

            def on_continue() -> None:
                self._credential_providers = [p for p, v in self._selected_providers.items() if v.get()]
                self._credential_index = 0
                self._show_credential_step()

            row = ttk.Frame(frame)
            row.pack(side="bottom", fill="x", pady=(16, 0))
            skip_all_button = ttk.Button(
                row, text=self.controller.text("bootstrap.credentials_skip_all_button"), command=self._show_finish
            )
            skip_all_button.pack(side="left")
            _tip(skip_all_button, self.controller.text("bootstrap.help.credentials_skip_all_button"))
            continue_button = ttk.Button(
                row, text=self.controller.text("bootstrap.credentials_continue_button"), command=on_continue
            )
            continue_button.pack(side="right")
            _tip(continue_button, self.controller.text("bootstrap.help.credentials_continue_button"))
            update_continue_state()

        self._set_frame(build)

    def _show_credential_step(self) -> None:
        """Shows the credential-entry screen for
        self._credential_providers[self._credential_index], or the finish
        screen once the index has moved past the end. Used both going
        forward (on_continue above, and _show_single_credential's own
        "Weiter") and going back (_show_single_credential's "Zurück") -
        walking a fixed list by index, rather than the previous
        pop-from-a-queue approach, is what makes going back to an
        already-shown provider possible at all (07.09.2026, "fehlt ein
        Zurückbutton wenn ich einen Provider ausgewählt habe").
        """
        if self._credential_index >= len(self._credential_providers):
            self._show_finish()
            return
        self._show_single_credential(self._credential_providers[self._credential_index])

    def _show_single_credential(self, provider: str) -> None:
        def build(frame: ttk.Frame) -> None:
            provider_label = self.controller.text(f"bootstrap.credentials_provider_{provider}")
            ttk.Label(frame, text=provider_label, font=("", 16, "bold")).pack(anchor="w")
            explain_key = f"bootstrap.credentials_explain_{provider}"
            ttk.Label(frame, text=self.controller.text(explain_key), wraplength=_TEXT_WRAP, justify="left").pack(
                anchor="w", pady=(8, 16)
            )
            open_signup_button = ttk.Button(
                frame,
                text=self.controller.text("bootstrap.credentials_open_signup_button"),
                command=lambda: self.controller.open_signup_page(provider),
            )
            open_signup_button.pack(anchor="w", pady=(0, 16))
            _tip(open_signup_button, self.controller.text("bootstrap.help.credential_open_signup_button"))

            ttk.Label(frame, text=self.controller.text("bootstrap.credentials_key_label", provider=provider_label)).pack(
                anchor="w"
            )
            key_var = tk.StringVar(value="")
            entry = ttk.Entry(frame, textvariable=key_var, show="*", width=50)
            entry.pack(anchor="w", pady=(4, 8))
            _tip(entry, self.controller.text("bootstrap.help.credential_key_entry"))
            status_var = tk.StringVar(value="")
            ttk.Label(frame, textvariable=status_var).pack(anchor="w")

            def on_save() -> None:
                value = key_var.get().strip()
                if not value:
                    return
                self.controller.save_provider_credential(provider, value)
                status_var.set(self.controller.text("bootstrap.credentials_saved"))

            save_button = ttk.Button(frame, text=self.controller.text("bootstrap.credentials_save_button"), command=on_save)
            save_button.pack(anchor="w", pady=(0, 16))
            _tip(save_button, self.controller.text("bootstrap.help.credential_save_button"))

            # 07.09.2026 ("Standard Vorstellung: Weiter deaktiviert wenn
            # nichts eingegeben ist"): this provider was explicitly
            # checked on the previous screen, so - unlike that screen's
            # own "Später in den Einstellungen" escape hatch - continuing
            # here with a still-empty field is disabled rather than
            # silently treated the same as skipping it. Going back and
            # unchecking the provider is the way to actually skip it now.
            def update_next_state(*_args: object) -> None:
                next_button.state(["!disabled"] if key_var.get().strip() else ["disabled"])

            key_var.trace_add("write", update_next_state)

            def go_back() -> None:
                self._credential_index -= 1
                if self._credential_index < 0:
                    self._show_credentials()
                else:
                    self._show_credential_step()

            def go_next() -> None:
                # 07.09.2026: previously a typed-but-not-explicitly-
                # "Gespeichert" key was silently discarded by "Weiter" -
                # save it here too (on_save() is a no-op on an empty
                # field, and this button stays disabled until non-empty
                # anyway) so the explicit Speichern click only ever
                # matters for its own status_var confirmation text, never
                # for whether the value actually persists.
                on_save()
                self._credential_index += 1
                self._show_credential_step()

            row = ttk.Frame(frame)
            row.pack(side="bottom", fill="x", pady=(16, 0))
            back_button = ttk.Button(row, text=self.controller.text("bootstrap.back_button"), command=go_back)
            back_button.pack(side="left")
            _tip(back_button, self.controller.text("bootstrap.help.back_button"))
            next_button = ttk.Button(
                row, text=self.controller.text("bootstrap.credentials_continue_button"), command=go_next
            )
            next_button.pack(side="right")
            _tip(next_button, self.controller.text("bootstrap.help.credentials_continue_button"))
            update_next_state()

        self._set_frame(build)

    # --- step 6: finish ------------------------------------------------

    def _show_finish(self) -> None:
        def build(frame: ttk.Frame) -> None:
            ttk.Label(frame, text=self.controller.text("bootstrap.finish_title"), font=("", 16, "bold")).pack(anchor="w")
            ttk.Label(frame, text=self.controller.text("bootstrap.finish_text"), wraplength=_TEXT_WRAP, justify="left").pack(
                anchor="w", pady=(8, 16)
            )

            def on_launch() -> None:
                self.controller.launch_app()
                self.destroy()

            row = ttk.Frame(frame)
            row.pack(side="bottom", fill="x", pady=(16, 0))
            close_button = ttk.Button(row, text=self.controller.text("bootstrap.finish_close_button"), command=self.destroy)
            close_button.pack(side="left")
            _tip(close_button, self.controller.text("bootstrap.help.finish_close_button"))
            launch_button = ttk.Button(row, text=self.controller.text("bootstrap.finish_launch_button"), command=on_launch)
            launch_button.pack(side="right")
            _tip(launch_button, self.controller.text("bootstrap.help.finish_launch_button"))

        self._set_frame(build, window_size=_FINISH_WINDOW_SIZE, show_cancel=False)


def _is_running_elevated() -> bool:
    """True if this process itself has Windows Administrator privileges.
    Always False elsewhere - elevation is a Windows/UAC-specific concept,
    there is nothing equivalent to guard against on macOS/Linux here."""
    import sys

    if sys.platform != "win32":
        return False
    import ctypes

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        # Fail open (assume not elevated): an unrelated ctypes/API problem
        # here should not block a normal, non-elevated install - it just
        # means this one safeguard silently does not run.
        return False


def _detect_wizard_language() -> str:
    """Best-effort language for the elevated-admin warning below - this
    runs before BootstrapController (or Tk) exists, so it cannot use
    self.controller.text() the way every other screen in this file does.

    07.09.2026 (real user report): the warning always appeared in German
    regardless of Windows' own UI language, which is fine for a German
    system but not otherwise. Matches against the FULL ui/i18n_data.py
    CATALOGUES (all 9 locales) rather than reusing
    bootstrap/system_lang.py::detect_system_language() - that function
    deliberately only recognizes "de"/"en" for the wizard's own initial
    language selection (a separate, documented scope decision - see its
    module docstring), which is not what "diese Meldung sollte in allen
    Sprachen verfuegbar sein" is asking for here. Falls back to "en" (not
    "de"), consistent with system_lang.py's own fallback choice.
    """
    from bootstrap import system_lang
    from ui.i18n_data import CATALOGUES

    raw = system_lang.raw_system_locale()
    if not raw:
        return "en"
    primary = raw.strip().lower().replace("_", "-").split("-", 1)[0]
    return primary if primary in CATALOGUES else "en"


def _warn_and_exit_if_elevated() -> bool:
    """Refuses to start if this process is running as Administrator, with
    a clear explanation instead of the confusing failure this causes
    hours or days later. Returns True if the caller should stop (a
    message was already shown and nothing else should run).

    06.09.2026 (real Windows install): a user's Start Menu shortcut and
    taskbar pin both failed completely silently - no window, no error, no
    bootstrap-crash.log or launch.log entry, not even a process appearing
    in Task Manager - while "Run as administrator" on the exact same
    shortcut worked. icacls on the venv's pythonw.exe showed only NT
    AUTHORITY\SYSTEM and BUILTIN\Administrators had any access to it at
    all - not the user's own account. bootstrap/paths.py's whole design
    is a per-user, admin-free install living under %LOCALAPPDATA% (see
    that module's docstring) - it already belongs to the current user
    without elevation. Running the *installer itself* "Als Administrator
    ausfuehren" defeats that: everything it then creates (the venv, the
    copied Python runtime, the extracted app, the Start Menu shortcut)
    ends up effectively owned by the Administrators group, so every
    later attempt to use any of it *without* elevation is denied by
    Windows before the process can even start - which is exactly why
    nothing could be observed anywhere, in any log, from a normal-
    privilege process afterwards.

    There is no reliable way to detect or repair this after the fact
    (a normal-privilege process cannot even read why it failed), so the
    only fix is to never let it happen: check at startup, before doing
    any work, and refuse with a clear explanation if elevated.

    07.09.2026: the message text now comes from ui/i18n_data.py's
    CATALOGUES (see _detect_wizard_language() above) instead of being a
    single hardcoded German string, and explicitly mentions that a
    standard Windows message box's text can be selected/copied with
    Ctrl+C - the same native behaviour _report_startup_crash() below
    already relies on, just not previously called out to the user.
    """
    import sys

    if not _is_running_elevated():
        return False

    from ui.i18n_data import CATALOGUES, DE

    catalogue = CATALOGUES.get(_detect_wizard_language(), DE)
    title = catalogue.get("bootstrap.elevated_warning_title", DE["bootstrap.elevated_warning_title"])
    message = catalogue.get("bootstrap.elevated_warning_text", DE["bootstrap.elevated_warning_text"])
    if sys.platform == "win32":
        import ctypes

        # MB_OK | MB_ICONWARNING.
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x30)
    else:
        print(f"{title}\n\n{message}", file=sys.stderr)
    return True


def main() -> None:
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        # This same executable doubles as its own uninstaller - the
        # standard NSIS/Inno Setup trick of one binary with an
        # "--uninstall" flag instead of a second PyInstaller build/CI
        # matrix just for this. See bootstrap/uninstall.py's module
        # docstring and bootstrap/installer.py::
        # register_windows_uninstall_entry(), which copies this exe
        # into install_root() and points Add/Remove Programs'
        # UninstallString at "<that copy> --uninstall".
        from bootstrap.uninstall import run_uninstall_ui

        run_uninstall_ui()
        return
    if _warn_and_exit_if_elevated():
        return
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


def _report_startup_crash(formatted_traceback: str | None = None) -> None:
    """Writes an exception to a log file and shows it in a way the user
    can actually copy - as opposed to PyInstaller's own --windowed crash
    dialog ("Unhandled exception in script"), which a user hit repeatedly
    during Windows testing (04.09.2026, Tcl/Tk version-mismatch bug - see
    .github/workflows/build-bootstrap.yml's Windows smoke-test step for
    the CI-side half of that story) and could only get to us as
    screenshots, since that particular dialog's text cannot be selected
    or saved. Called from two places: main()'s except block (no argument,
    formats sys.exc_info() itself) for a crash during startup, and
    BootstrapApp.report_callback_exception (formatted_traceback given
    explicitly, since tkinter hands that hook exc/val/tb directly rather
    than leaving them in sys.exc_info()) for a crash inside a widget
    callback partway through the wizard.

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

    tb = formatted_traceback if formatted_traceback is not None else traceback.format_exc()
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
