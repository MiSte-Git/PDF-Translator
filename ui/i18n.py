"""Small runtime UI catalogue with prepared future locales.

The plain-data catalogue (LocaleInfo/LOCALES/DE/EN/CATALOGUES) moved to
ui/i18n_data.py on 26.08.2026 - see that module's docstring for why (in
short: webapp/, the new local-server+pywebview UI, must never import
PySide6, but the string tables themselves are Qt-independent and worth
sharing rather than duplicating). Re-exported below unchanged so every
existing `from ui.i18n import DE`/`CATALOGUES`/etc. keeps working exactly
as before - only LanguageManager, the one genuinely Qt-specific piece
(QObject/Signal for retranslation notifications), stays defined here.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ui.i18n_data import CATALOGUES, DE, EN, LOCALES, LocaleInfo  # noqa: F401 - re-exported for existing callers


class LanguageManager(QObject):
    changed = Signal(str)

    def __init__(self, language: str = "de") -> None:
        super().__init__()
        self.language = language if language in CATALOGUES else "de"

    def set_language(self, language: str) -> None:
        if language not in CATALOGUES or language == self.language:
            return
        self.language = language
        self.changed.emit(language)

    def text(self, key: str, **values: object) -> str:
        template = CATALOGUES[self.language].get(key, DE.get(key, key))
        return template.format(**values) if values else template
