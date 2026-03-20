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
    music_credits: list[dict] | None = None  # [{title, artist, album}] from Content ID
    error: str | None = None


def detect_platform(url: str) -> str | None:
    """Detect which platform a URL belongs to."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(host):
            return platform
    return None


def extract_youtube_music_credits(url: str) -> list[dict]:
    """Extract Content ID music credits from a YouTube video page.

    YouTube's "Music in this video" / "Música" section contains structured
    track data (title, artist, album) from Content ID matches. This data
    isn't available via yt-dlp, so we scrape it from the page's ytInitialData.

    Returns list of dicts: [{title, artist, album}, ...]
    """
    try:
        import requests
    except ImportError:
        logger.debug("requests not installed, skipping music credits extraction")
        return []

    try:
        import json as _json

        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        match = re.search(
            r"var ytInitialData\s*=\s*({.*?});</script>", resp.text, re.DOTALL
        )
        if not match:
            logger.debug("No ytInitialData found in page")
            return []

        data = _json.loads(match.group(1))

        # Music credits live in engagementPanels → structuredDescriptionContentRenderer
        # → horizontalCardListRenderer → cards[] → videoAttributeViewModel
        credits: list[dict] = []
        panels = data.get("engagementPanels", [])
        for panel in panels:
            renderer = (
                panel
                .get("engagementPanelSectionListRenderer", {})
                .get("content", {})
                .get("structuredDescriptionContentRenderer", {})
                .get("items", [])
            )
            for item in renderer:
                card_list = item.get("horizontalCardListRenderer", {}).get("cards", [])
                for card in card_list:
                    vm = card.get("videoAttributeViewModel", {})
                    title = vm.get("title")
                    artist = vm.get("subtitle")
                    album = None
                    secondary = vm.get("secondarySubtitle")
                    if isinstance(secondary, dict):
                        album = secondary.get("content")
                    elif isinstance(secondary, str):
                        album = secondary

                    if title and artist:
                        credits.append({
                            "title": title,
                            "artist": artist,
                            "album": album,
                        })

        if credits:
            logger.info("Found %d music credits from Content ID", len(credits))
        return credits

    except Exception:
        logger.debug("Failed to extract YouTube music credits", exc_info=True)
        return []


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

        # Extract Content ID music credits for YouTube
        music_credits = None
        if platform == "youtube":
            music_credits = extract_youtube_music_credits(url) or None

        return ExtractedMetadata(
            url=url,
            platform=platform,
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel"),
            description=info.get("description"),
            duration_sec=info.get("duration"),
            chapters=info.get("chapters"),
            comments=comments,
            music_credits=music_credits,
        )

    except Exception as e:
        logger.exception("yt-dlp extraction failed for %s", url)
        return ExtractedMetadata(
            url=url, platform=platform,
            error=f"Extraction failed: {e}"
        )
