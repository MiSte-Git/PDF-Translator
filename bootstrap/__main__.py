"""Entry point for `python -m bootstrap` and for the PyInstaller build
(.github/workflows/build-bootstrap.yml points its --name/entry script here).
"""
from __future__ import annotations

from bootstrap.app import main

if __name__ == "__main__":
    main()
