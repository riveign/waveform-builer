"""Dash application factory for the waveform visualizer."""

from __future__ import annotations

from pathlib import Path

from dash import Dash
from flask import abort, send_file

from djsetbuilder.config import VISUALIZER_PORT
from djsetbuilder.db.models import Track, get_session
from djsetbuilder.visualization.callbacks import register_callbacks
from djsetbuilder.visualization.layout import build_main_layout

ASSETS_DIR = Path(__file__).parent / "assets"

MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
}


def create_app(debug: bool = False) -> Dash:
    """Create and configure the Dash waveform visualizer app."""
    app = Dash(
        __name__,
        assets_folder=str(ASSETS_DIR),
        title="DJ Set Builder — Waveform Visualizer",
        suppress_callback_exceptions=True,
    )

    app.layout = build_main_layout()
    register_callbacks(app)
    _register_audio_route(app)

    return app


def _register_audio_route(app: Dash) -> None:
    """Add /audio/<track_id> streaming route to the underlying Flask server."""

    @app.server.route("/audio/<int:track_id>")
    def serve_audio(track_id: int):
        session = get_session()
        track = session.query(Track).get(track_id)
        if not track or not track.file_path:
            abort(404)

        path = Path(track.file_path)
        if not path.exists():
            abort(404)

        mimetype = MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return send_file(path, mimetype=mimetype, conditional=True)


def run_visualizer(
    port: int = VISUALIZER_PORT,
    debug: bool = False,
    track_query: str | None = None,
    set_name: str | None = None,
) -> None:
    """Launch the waveform visualizer web app."""
    app = create_app(debug=debug)

    url = f"http://localhost:{port}"
    if track_query:
        print(f"Pre-loading track: {track_query}")
    if set_name:
        print(f"Pre-loading set: {set_name}")

    print(f"\n  Waveform Visualizer running at {url}\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
