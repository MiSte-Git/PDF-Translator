"""Background workers for the Qt UI."""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ui.analysis import analyze_request
from ui.models import AnalysisResult, TranslationRequest


class AnalysisSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class AnalysisWorker(QRunnable):
    def __init__(self, request: TranslationRequest, max_chars_per_run: int) -> None:
        super().__init__()
        self.request = request
        self.max_chars_per_run = max_chars_per_run
        self.signals = AnalysisSignals()

    @Slot()
    def run(self) -> None:
        try:
            result: AnalysisResult = analyze_request(self.request, self.max_chars_per_run)
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)
