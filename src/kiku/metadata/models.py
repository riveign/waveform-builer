"""Normalized data shapes shared across every metadata source.

A source's job is to turn its raw response (Bandcamp HTML, Discogs JSON, MB JSON,
embedded tags) into a `ReleaseCandidate`. Everything downstream — fuzzy matching,
diff building, applying — speaks only these shapes, never a source's wire format.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Identity fields a correction is allowed to touch, in display order.
CORRECTABLE_FIELDS: tuple[str, ...] = (
    "title",
    "artist",
    "album",
    "label",
    "release_year",
    "track_number",
    "disc_number",
)


@dataclass
class RecordingCandidate:
    """One track as described by a source."""

    title: str
    position: int | None = None
    disc: int | None = None
    artist: str | None = None  # per-track artist (compilations / remixers)
    length_ms: int | None = None


@dataclass
class ReleaseCandidate:
    """One release (album/EP) as described by a source."""

    source: str  # "bandcamp" | "musicbrainz" | "discogs" | "tags"
    source_id: str  # MB release id, Discogs release id, bandcamp URL, "embedded"
    album: str | None = None
    artist: str | None = None
    label: str | None = None
    year: int | None = None
    url: str | None = None
    recordings: list[RecordingCandidate] = field(default_factory=list)

    @property
    def track_count(self) -> int:
        return len(self.recordings)


@dataclass
class FieldChange:
    """A single field's old→new transition for one track."""

    field: str
    old: str | int | None
    new: str | int | None

    @property
    def changed(self) -> bool:
        """True when applying this would actually alter the value.

        Empty/None proposals are never changes — a source that doesn't know a
        field must not blank out one we already have.
        """
        if self.new is None or (isinstance(self.new, str) and not self.new.strip()):
            return False
        return self._norm(self.new) != self._norm(self.old)

    @staticmethod
    def _norm(v: str | int | None) -> str:
        if v is None:
            return ""
        return str(v).strip().lower()


@dataclass
class TrackCorrection:
    """All proposed field changes for one library track + match confidence."""

    track_id: int
    matched_title: str | None  # the source recording we aligned to
    confidence: float
    changes: list[FieldChange] = field(default_factory=list)

    def change_for(self, field_name: str) -> FieldChange | None:
        return next((c for c in self.changes if c.field == field_name), None)

    @property
    def has_changes(self) -> bool:
        return any(c.changed for c in self.changes)
