"""Environment-variable and optional OS-keyring access to API keys.

Environment variables are checked first by default, for machines that have
not yet been migrated to an OS keyring - and, deliberately, so a caller can
override a stored key for a single subprocess call without touching the
keyring at all (see image_translate_cli/CLI.md's "Zugangsdaten für den
Provider" section: TME passes its own DEEPL_API_KEY via `env={...}` for one
`translate`/`check` invocation - see get_api_key()'s env_first parameter).
There is deliberately no plaintext credentials file fallback.

02.09.2026 (Michael, after reloading Drive credentials from a downloaded
JSON file and re-saving made no difference): env-first is the wrong default
for a value the app's own UI is meant to be the sole source of truth for -
a stray environment variable left over from an earlier debugging session
(e.g. in .bashrc) then silently and permanently overrides whatever the
"speichern" button just wrote, with no visible sign anything is wrong. The
four Google-Drive-OAuth getters near the bottom of this file pass
env_first=False for exactly that reason: keyring (i.e. what the UI saved)
wins, environment variables are only a fallback for a value that was never
saved at all. The four translation-provider getters above them keep the
default env_first=True, since TME's documented per-call override relies on
it.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

# Service name under which all provider API keys are stored in the OS
# keyring (Windows Credential Locker / macOS Keychain / Secret Service on
# Linux).
_KEYRING_SERVICE = "pdf-translator"


def _keyring_module():
    try:
        import keyring
    except ImportError:
        return None
    return keyring


def get_api_key(key_name: str, env_names: tuple[str, ...] = (), env_first: bool = True) -> str:
    """Read an API key from the environment and the optional keyring.

    ``env_names`` are checked in order, followed by the uppercase key name.
    Keyring import/backend errors are treated as an unavailable fallback and
    reported without exposing any credential value.

    ``env_first`` (default True) picks which source wins when both an
    environment variable AND a keyring entry are present for the same
    ``key_name`` - see this module's docstring for why the default differs
    from the Google-Drive-OAuth getters (env_first=False there). When only
    one source has a value, this parameter has no effect - the one present
    value is used either way.
    """
    # dict.fromkeys() dedupes while preserving order - without it, a
    # get_*_api_key() helper whose env_names already equals key_name.upper()
    # (e.g. get_deepl_api_key(): env_names=("DEEPL_API_KEY",),
    # key_name="deepl_api_key") listed that same variable twice in the
    # error message below (found 22.08.2026 while building
    # image_translate_cli's `check` command, which surfaces this message
    # to a caller like TME - see CLI.md).
    # 02.09.2026 (Michael: "Haben wir kein Log für genau solche Fälle?",
    # nachdem ein im UI neu gespeicherter Wert scheinbar wirkungslos
    # blieb) - Loggt NUR die Quelle (env-Variablenname oder
    # "Schlüsselbund"), NIE den Wert selbst - auch nicht bei vermeintlich
    # unkritischen Feldern wie einer Projekt-ID, denn genau der Bug, der
    # zu dieser Zeile führte, zeigt, dass dort auch mal ein echtes
    # Geheimnis (ein API-Schlüssel) drinstehen kann.
    candidates = tuple(dict.fromkeys((*env_names, key_name.upper())))

    def _from_env() -> str | None:
        for env_name in candidates:
            value = os.environ.get(env_name)
            if value and value.strip():
                log.debug("%s: geladen aus Umgebungsvariable %s", key_name, env_name)
                return value.strip()
        return None

    def _from_keyring() -> str | None:
        keyring = _keyring_module()
        if keyring is None:
            return None
        try:
            value = keyring.get_password(_KEYRING_SERVICE, key_name)
        except Exception as exc:  # backend not installed/configured
            log.debug("%s: Zugriff auf den OS-Schlüsselbund fehlgeschlagen: %s", key_name, exc)
            return None
        if value and value.strip():
            log.debug("%s: geladen aus dem OS-Schlüsselbund", key_name)
            return value.strip()
        return None

    sources = (_from_env, _from_keyring) if env_first else (_from_keyring, _from_env)
    for source in sources:
        value = source()
        if value is not None:
            return value

    log.debug("%s: keine Zugangsdaten gefunden (weder Umgebungsvariable noch Schlüsselbund)", key_name)
    raise RuntimeError(
        f"No credential available for {key_name!r}. Set one of the environment "
        f"variables {', '.join(candidates)} or configure OS keyring service "
        f"{_KEYRING_SERVICE!r}."
    )


def set_api_key(key_name: str, value: str) -> None:
    """Store an API key in the OS keyring under _KEYRING_SERVICE."""
    value = value.strip()
    if not value:
        raise ValueError("Cannot store an empty API key")
    keyring = _keyring_module()
    if keyring is None:
        raise RuntimeError("The optional 'keyring' package is not installed")
    try:
        keyring.set_password(_KEYRING_SERVICE, key_name, value)
    except Exception as exc:
        raise RuntimeError(f"OS keyring is unavailable: {exc}") from exc


def has_api_key(key_name: str, env_names: tuple[str, ...] = (), env_first: bool = True) -> bool:
    """True if get_api_key(key_name, env_names, env_first) would succeed,
    without raising.

    Added 01.09.2026 for the Google-Drive-Ordnersuche feature: unlike every
    other credential in this module (which either IS configured at startup
    via env/keyring, or the whole provider is simply unusable), Drive OAuth
    has three distinct, UI-relevant states - "not configured at all",
    "configured but not yet connected", "connected" - and the UI needs to
    check each one without ever triggering get_api_key()'s RuntimeError as
    control flow. ``env_first`` only affects WHICH source wins when both
    have a value - it never changes this function's True/False result, so
    passing it through is purely for signature symmetry with get_api_key().
    """
    try:
        get_api_key(key_name, env_names, env_first=env_first)
    except RuntimeError:
        return False
    return True


def delete_api_key(key_name: str) -> None:
    """Remove a keyring-stored credential (no-op if it was never stored).

    Deliberately does NOT touch any environment variable of the same name -
    an env var was set outside this app's control and clearing it here would
    be surprising. Used by the Google-Drive "Trennen" (disconnect) action to
    drop the stored refresh token; a still-set GOOGLE_DRIVE_REFRESH_TOKEN env
    var would keep overriding this either way (see get_api_key()'s env-first
    order), which is documented at the call site.
    """
    keyring = _keyring_module()
    if keyring is None:
        return
    try:
        keyring.delete_password(_KEYRING_SERVICE, key_name)
    except Exception:
        pass  # nothing stored under this name, or backend unavailable - fine


def get_google_translate_api_key() -> str:
    """Google Cloud Translation API key from the OS keyring."""
    return get_api_key("google_translate_api_key", ("GOOGLE_TRANSLATE_API_KEY",))


def get_deepl_api_key() -> str:
    """DeepL API key from the OS keyring."""
    return get_api_key("deepl_api_key", ("DEEPL_API_KEY",))


def get_openai_api_key() -> str:
    """OpenAI API key from the OS keyring."""
    return get_api_key("openai_api_key", ("OPENAI_API_KEY",))


def get_grok_api_key() -> str:
    """xAI Grok API key from the OS keyring."""
    return get_api_key("grok_api_key", ("GROK_API_KEY", "XAI_API_KEY"))


# --- Google Drive OAuth (01.09.2026, Google-Drive-Ordnersuche) -------------
#
# Unlike the four translation providers above, Drive access is not a single
# static API key: it is a per-user OAuth "installed app" client (Client-ID +
# Client-Secret, created once by the user in Google Cloud Console - this app
# cannot provision that itself) plus a refresh token obtained by an
# interactive consent flow (see pipeline/drive_auth.py::connect_interactively()).
# All three pieces are still just opaque strings from this module's point of
# view, so they reuse get_api_key()/set_api_key()/has_api_key() as-is rather
# than needing new storage machinery.
#
# 02.09.2026 (Michael, after re-loading+re-saving Drive credentials from a
# downloaded JSON file appeared to change nothing): env_first=False on all
# four getters below - unlike the translation-provider keys above (which
# deliberately keep env-first for TME's documented per-call override, see
# this module's own docstring), Drive OAuth is configured exclusively
# through this app's own dialog. There is no legitimate reason for a
# leftover environment variable to permanently out-rank whatever the
# "Zugangsdaten speichern"/OAuth-sign-in flow just stored - it can only ever
# be a stale value from an earlier debugging session silently winning.

def get_google_drive_client_id() -> str:
    """OAuth Client-ID for the Drive-Ordnersuche feature, from the OS keyring."""
    return get_api_key("google_drive_client_id", ("GOOGLE_DRIVE_CLIENT_ID",), env_first=False)


def get_google_drive_client_secret() -> str:
    """OAuth Client-Secret for the Drive-Ordnersuche feature, from the OS keyring."""
    return get_api_key("google_drive_client_secret", ("GOOGLE_DRIVE_CLIENT_SECRET",), env_first=False)


def get_google_drive_project_id() -> str:
    """Google Cloud project ID the OAuth client belongs to, from the OS keyring.

    Added 02.09.2026 (Michael: "Mit Google verbinden" failed - "die Google
    Projekt-ID fehlt"). Every OAuth "Desktop app" client Google Cloud
    Console lets you create belongs to exactly one project - the
    `client_secret_....json` Google itself offers for download always
    includes a "project_id" field alongside client_id/client_secret, but
    the original docs/google_drive_setup.md only ever asked for the latter
    two, and connect_interactively()/build_service() never passed one
    along either. Without it, the OAuth credentials this app mints have no
    associated quota project (see google.oauth2.credentials.Credentials'
    `quota_project_id` - see pipeline/drive_auth.py::build_service()),
    which is exactly what surfaces to the user as a Google-side "project"
    error when calling the Drive API.
    """
    return get_api_key("google_drive_project_id", ("GOOGLE_DRIVE_PROJECT_ID",), env_first=False)


def get_google_drive_refresh_token() -> str:
    """Stored OAuth refresh token from a previous successful Google sign-in."""
    return get_api_key("google_drive_refresh_token", ("GOOGLE_DRIVE_REFRESH_TOKEN",), env_first=False)
