"""Shared HTTP helpers for cover-art image downloads."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "Kiku/0.1 ( riveign@gmail.com )"
DEFAULT_TIMEOUT_S = 20.0
MAX_BYTES = 8 * 1024 * 1024  # 8 MB sanity cap


def download_image(
    url: str,
    *,
    transport: httpx.BaseTransport | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> tuple[bytes, str] | None:
    """Fetch an image URL → (bytes, content_type), or None on any failure.

    Soft-fail by design: a bad URL, non-200, oversized body, or network error
    all return None so the resolver falls through to the next source instead of
    surfacing an error.
    """
    try:
        with httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            resp = client.get(url)
    except httpx.HTTPError:
        logger.warning("Image download failed for %s", url, exc_info=True)
        return None

    if resp.status_code != 200:
        logger.info("Image download for %s returned %s", url, resp.status_code)
        return None

    content = resp.content
    if not content or len(content) > MAX_BYTES:
        logger.warning("Image at %s rejected (size=%d)", url, len(content or b""))
        return None

    content_type = resp.headers.get("content-type", "image/jpeg")
    return content, content_type
