"""Standalone CLI/subprocess interface for the image-translation pipeline
(pipeline/images/) - Backlog.md "Geplant", 22.08.2026: "Bildübersetzung als
eigenständige, in andere Programme einbindbare Schnittstelle bauen".

Does not belong under pipeline/ - pipeline/images stays a generic library
(OCR + translate + inpaint one image, no notion of a command line, a config
file, or a JSON report). This package is the thin, stable, documented
wrapper around that library meant for OTHER PROGRAMS (initially TME,
github.com/MiSte-Git/TME, which runs on the same machine today but is
meant to be able to run standalone later - see Backlog.md) to call via
subprocess, without depending on pipeline/images/'s internal APIs, which
are still in flux, or on anything under ui/ (a desktop-UI-specific
package). See CLI.md for the full command-line contract, the config file
schema, and the JSON report schema - all three are versioned so a caller
can detect a future incompatible change instead of guessing.

Mirrors ico_translate/ (a different top-level CLI package, application
layer for the one ICO Google-Drive folder) in being a top-level package
rather than nested under pipeline/, but for the opposite reason: ico_translate
is deliberately project-specific glue on top of the generic engine, while
image_translate_cli is deliberately generic - project-agnostic - so any
other program (not just TME) can embed it the same way.
"""
