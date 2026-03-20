"""URL router and metadata extractor for Track Hunter.

Uses yt-dlp to extract descriptions, chapters, and comments from
SoundCloud, YouTube, and Mixcloud URLs without downloading audio.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

PLATFORM_PATTERNS = {
    "youtube": re.compile(r"(youtube\.com|youtu\.be)"),
    "soundcloud": re.compile(r"soundcloud\.com"),
    "mixcloud": re.compile(r"mixcloud\.com"),
    "1001tracklists": re.compile(r"1001tracklists\.com"),
}


@dataclass
class ExtractedMetadata:
    """Raw metadata extracted from a URL."""
    url: str
    platform: str
    title: str | None = None
    uploader: str | None = None
    description: str | None = None
    duration_sec: float | None = None
    chapters: list[dict] | None = None  # [{title, start_time, end_time}]
    comments: list[dict] | None = None  # [{text, timestamp, author}]
    error: str | None = None


def detect_platform(url: str) -> str | None:
    """Detect which platform a URL belongs to."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(host):
            return platform
    return None


def extract_metadata(url: str, include_comments: bool = True) -> ExtractedMetadata:
    """Extract metadata from a URL using yt-dlp.

    Args:
        url: The URL to extract from.
        include_comments: Whether to fetch comments (slower, but valuable for track IDs).

    Returns:
        ExtractedMetadata with all available information.
    """
    platform = detect_platform(url)
    if platform == "1001tracklists":
        return ExtractedMetadata(url=url, platform="1001tracklists")

    if platform is None:
        return ExtractedMetadata(url=url, platform="unknown", error="Unsupported URL")

    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        return ExtractedMetadata(
            url=url, platform=platform or "unknown",
            error="yt-dlp not installed. Run: pip install 'kiku[hunting]'"
        )

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    if include_comments:
        opts["getcomments"] = True

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info is None:
            return ExtractedMetadata(url=url, platform=platform, error="No metadata returned")

        comments = None
        if include_comments and info.get("comments"):
            comments = [
                {
                    "text": c.get("text", ""),
                    "timestamp": c.get("timestamp"),
                    "author": c.get("author", ""),
                }
                for c in info["comments"]
            ]

        return ExtractedMetadata(
            url=url,
            platform=platform,
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel"),
            description=info.get("description"),
            duration_sec=info.get("duration"),
            chapters=info.get("chapters"),
            comments=comments,
        )

    except Exception as e:
        logger.exception("yt-dlp extraction failed for %s", url)
        return ExtractedMetadata(
            url=url, platform=platform,
            error=f"Extraction failed: {e}"
        )
