"""Multi-source metadata correction.

Check and correct library entries (title/artist/album/label/year/track order)
against external sources — Bandcamp, MusicBrainz, Discogs, or the files' own
embedded tags — always behind a before→after preview the DJ confirms.
"""

from kiku.metadata.models import RecordingCandidate, ReleaseCandidate, TrackCorrection

__all__ = ["RecordingCandidate", "ReleaseCandidate", "TrackCorrection"]
