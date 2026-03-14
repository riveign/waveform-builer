"""Dash application factory for the waveform visualizer."""

from __future__ import annotations

from pathlib import Path

from dash import Dash

from djsetbuilder.config import VISUALIZER_PORT
from djsetbuilder.visualization.callbacks import register_callbacks
from djsetbuilder.visualization.layout import build_main_layout

ASSETS_DIR = Path(__file__).parent / "assets"


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

    return app


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
