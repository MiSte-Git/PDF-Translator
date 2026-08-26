"""Local-server + pywebview replacement for the images-mode Qt UI.

Walking-skeleton pilot (Backlog.md 26.08.2026 "lokaler Server +
pywebview"): a stdlib-only `http.server` bound to 127.0.0.1, paired with
a native pywebview app window, covering the image-translation flow end
to end (pick source images -> configure -> cost-confirmation gate -> run
-> QA report -> optional manual correction via
image_translate_cli/review_server.py). PDF/Word/PPTX stay on the
existing PySide6 app (ui/) until this pilot proves out - see the plan
this package was built from for the full reasoning and sequencing.

The HTTP layer - server.py, job_bridge.py, settings_store.py, and
everything they import from ui/pipeline/ - must never import PySide6/
PyQt (verified by tests/test_webapp_*.py's own PySide6-blocked import
check). That is what keeps this package testable and runnable outside a
GUI/display, exactly the property ui/i18n_data.py was split out of
ui/i18n.py for (see that module's own docstring) and why server.py/
job_bridge.py reuse ui/models.py/pipeline/registry.py directly instead
of anything Qt-flavored.

__main__.py (Schritt 6, the pywebview app-shell bootstrap) is the one
deliberate exception: its whole job is opening a native GUI window, so
it depends on Qt via pywebview's own Qt/QtWebEngine backend - the same
PySide6 the existing ui/ Qt app already requires, not a new toolkit.
That dependency stays contained to __main__.py; the HTTP layer it
starts on a background thread stays exactly as Qt-free as before.
"""
