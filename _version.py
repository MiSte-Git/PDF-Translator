"""Single source of truth for this project's version number.

01.09.2026 (Michael: "Haben wir schon einen Stand um eine Version draus zu
machen? Dann lass uns das Update angehen.") - introduced together with the
self-update feature (ui/app.py's startup update check, reusing
bootstrap/release_source.py's GitHub Release API code), which needs
SOMETHING to compare the running app against the latest GitHub release.
There was no version number anywhere in the project before this.

Read from three places, each for a different reason:
- ui/app.py imports __version__ directly to compare against
  bootstrap.release_source.check_for_update()'s result and to show in the
  "Über"/about text.
- .github/workflows/build-bootstrap.yml's build-source-archive job reads
  this file (a small `python -c "from _version import __version__; ..."`
  check) and fails the whole release BEFORE anything gets published if the
  pushed `vX.Y.Z` tag and __version__ here disagree - the tag is what
  triggers a release and what bootstrap/release_source.py's GitHub API
  calls key off of, __version__ is what a running app compares itself
  against, and those two must never silently drift apart (forgetting to
  bump one of them would otherwise ship a release that either never shows
  up as an update to existing installs, or shows up as one forever).
- bootstrap/release_source.py's own tests construct expected values against
  this - see tests/test_bootstrap_release_source.py.

Deliberately a plain top-level module, not inside pipeline/ or ui/: bootstrap/
(see its own __init__.py docstring) may not import from pipeline/ or ui/
(other than two explicitly whitelisted, dependency-free exceptions, and this
isn't one of them) but DOES need this value for a future "which version am I
about to reinstall over" check - a bare top-level module with a single
string constant and zero imports is safe for every part of this project
(bootstrap/, pipeline/, ui/, image_translate_cli/, webapp/) to import without
pulling in anything else.

**How to release a new version** (see also README.md's "Release-Prozess" -
mirrors that section, kept in sync by hand since both explain the same
process to two different audiences: this docstring to whoever edits this
file, that section to whoever runs the release):
1. Bump __version__ below (semver: MAJOR.MINOR.PATCH - see
   https://semver.org).
2. Commit that change on its own ("Version X.Y.Z").
3. `git tag vX.Y.Z && git push origin vX.Y.Z` - the leading "v" on the tag
   is a GitHub/git convention, NOT part of __version__ itself (compare
   bootstrap/release_source.py's version parsing, which strips it back off
   before comparing).
4. .github/workflows/build-bootstrap.yml's `push: tags: v*` trigger builds
   the bootstrapper executables AND attaches the app-source Release ZIP
   asset (see bootstrap/release_source.py's module docstring for why a ZIP
   rather than a git clone) that both a fresh install and every existing
   install's self-update check download from.
"""
from __future__ import annotations

__version__ = "0.1.1"
