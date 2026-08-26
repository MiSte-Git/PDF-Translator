"""Local-server + pywebview replacement for the images-mode Qt UI.

Walking-skeleton pilot (Backlog.md 26.08.2026 "lokaler Server +
pywebview"): a stdlib-only `http.server` bound to 127.0.0.1, paired with
a native pywebview app window, covering the image-translation flow end
to end (pick source images -> configure -> cost-confirmation gate -> run
-> QA report -> optional manual correction via
image_translate_cli/review_server.py). PDF/Word/PPTX stay on the
existing PySide6 app (ui/) until this pilot proves out - see the plan
this package was built from for the full reasoning and sequencing.

Must never import PySide6/PyQt - that is the whole point of this
package existing as a separate process/UI from ui/. Reuses ui/models.py
(already Qt-independent, see that module's own docstring),
ui/i18n_data.py (split out of ui/i18n.py on the same date for exactly
this reason), and pipeline/registry.py directly.
"""
