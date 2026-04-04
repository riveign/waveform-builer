"""SoundCloud OAuth 2.1 with PKCE helpers."""

from __future__ import annotations

import hashlib
import secrets
from base64 import urlsafe_b64encode
from urllib.parse import urlencode

from kiku.config import _get

SC_AUTH_URL = "https://soundcloud.com/connect"
SC_TOKEN_URL = "https://api.soundcloud.com/oauth2/token"

# Module-level PKCE state (single-user app, one auth flow at a time)
_code_verifier: str | None = None


def _get_sc_config() -> tuple[str, str]:
    """Return (client_id, client_secret) from ~/.kiku/config.toml."""
    client_id = _get("soundcloud", "client_id", None)
    client_secret = _get("soundcloud", "client_secret", None)
    if not client_id or not client_secret:
        raise ValueError(
            "SoundCloud credentials not configured. "
            "Add [soundcloud] client_id and client_secret to ~/.kiku/config.toml"
        )
    return client_id, client_secret


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def get_auth_url(redirect_uri: str) -> str:
    """Build SoundCloud OAuth authorization URL with PKCE."""
    global _code_verifier
    client_id, _ = _get_sc_config()
    _code_verifier, code_challenge = _generate_pkce()

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": "non-expiring",
    }
    return f"{SC_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for tokens."""
    import httpx

    global _code_verifier
    client_id, client_secret = _get_sc_config()

    if not _code_verifier:
        raise ValueError("No PKCE verifier — start auth flow first via get_auth_url()")

    resp = httpx.post(
        SC_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "code_verifier": _code_verifier,
        },
    )
    resp.raise_for_status()
    _code_verifier = None
    return resp.json()


def refresh_token(current_refresh_token: str) -> dict:
    """Refresh an expired access token."""
    import httpx

    client_id, client_secret = _get_sc_config()

    resp = httpx.post(
        SC_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": current_refresh_token,
        },
    )
    resp.raise_for_status()
    return resp.json()
