"""Dash callback handlers for the waveform visualizer."""

from __future__ import annotations

import json

from dash import Input, Output, State, callback_context, html, no_update

from djsetbuilder.db.models import AudioFeatures, Set, SetTrack, Track, TransitionCue, get_session
from djsetbuilder.db.store import get_track_by_title, search_tracks
from djsetbuilder.visualization.figures import (
    build_overview_figure,
    build_set_timeline_figure,
    build_track_figure,
    build_transition_figure,
)
from djsetbuilder.visualization.layout import build_set_tab, build_track_tab


def register_callbacks(app):
    """Register all Dash callbacks on the app."""

    # --- Tab switching ---
    @app.callback(
        Output("tab-content", "children"),
        Input("main-tabs", "value"),
    )
    def render_tab(tab):
        if tab == "track-tab":
            return build_track_tab()
        elif tab == "set-tab":
            return build_set_tab()
        return html.Div()

    # --- Track selector options ---
    @app.callback(
        Output("track-selector", "options"),
        Input("track-selector", "search_value"),
    )
    def update_track_options(search):
        session = get_session()
        if search and len(search) >= 2:
            tracks = search_tracks(session, title=search)
        else:
            # Show analyzed tracks
            tracks = (
                session.query(Track)
                .join(AudioFeatures)
                .filter(AudioFeatures.waveform_overview.isnot(None))
                .order_by(Track.title)
                .limit(50)
                .all()
            )
        return [
            {
                "label": f"{t.title or '?'} — {t.artist or '?'} ({t.bpm:.0f} BPM, {t.key or '?'})" if t.bpm else f"{t.title or '?'} — {t.artist or '?'}",
                "value": t.id,
            }
            for t in tracks
        ]

    # --- Track selection: load waveforms ---
    @app.callback(
        [
            Output("track-info", "children"),
            Output("track-info", "style"),
            Output("overview-graph", "figure"),
            Output("detail-graph", "figure"),
            Output("current-track-id", "data"),
            Output("cue-list", "children"),
        ],
        Input("track-selector", "value"),
        State("current-set-id", "data"),
    )
    def load_track(track_id, set_id):
        if not track_id:
            return no_update, {"display": "none"}, no_update, no_update, no_update, no_update

        session = get_session()
        track = session.query(Track).get(track_id)
        if not track:
            return no_update, {"display": "none"}, no_update, no_update, no_update, no_update

        af = track.audio_features

        # Track info bar
        info = html.Div([
            html.Span(track.title or "Unknown", className="title"),
            html.Span(f" — {track.artist or 'Unknown'}", className="meta"),
            html.Span(f"{track.bpm:.0f} BPM" if track.bpm else "", className="badge badge-bpm",
                       style={"marginLeft": "16px"}),
            html.Span(track.key or "", className="badge badge-key", style={"marginLeft": "4px"}),
            html.Span(track.dir_genre or track.rb_genre or "", className="badge badge-genre",
                       style={"marginLeft": "4px"}),
            html.Span(track.dir_energy or "", className="badge badge-energy", style={"marginLeft": "4px"}),
        ], className="track-info")

        if not af or not af.waveform_overview:
            overview_fig = build_overview_figure(track, af)
            detail_fig = build_track_figure(track, af)
            return info, {"display": "block"}, overview_fig, detail_fig, track_id, _build_cue_list(session, set_id, track_id)

        # Build figures
        overview_fig = build_overview_figure(track, af)

        # Load cue points for this track
        cues = _get_cue_dicts(session, set_id, track_id)
        detail_fig = build_track_figure(track, af, use_detail=True, cue_points=cues)

        return info, {"display": "block"}, overview_fig, detail_fig, track_id, _build_cue_list(session, set_id, track_id)

    # --- Click on detail waveform: show time for cue creation ---
    @app.callback(
        Output("cue-click-info", "children"),
        Input("detail-graph", "clickData"),
    )
    def show_click_time(click_data):
        if not click_data or not click_data.get("points"):
            return "Click on waveform to place a cue point"
        point = click_data["points"][0]
        time_sec = point.get("x", 0)
        minutes = int(time_sec // 60)
        seconds = time_sec % 60
        return f"Selected: {minutes}:{seconds:05.2f} ({time_sec:.3f}s) — Enter name and press Enter to save"

    # --- Save cue point on Enter in name input ---
    @app.callback(
        [Output("cue-list", "children", allow_duplicate=True),
         Output("cue-name-input", "value")],
        Input("cue-name-input", "n_submit"),
        [
            State("cue-name-input", "value"),
            State("cue-type-selector", "value"),
            State("cue-slot-selector", "value"),
            State("detail-graph", "clickData"),
            State("current-track-id", "data"),
            State("current-set-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_cue(n_submit, name, cue_type, slot, click_data, track_id, set_id):
        if not name or not click_data or not track_id:
            return no_update, no_update

        point = click_data["points"][0]
        start_sec = point.get("x", 0)

        session = get_session()
        cue = TransitionCue(
            set_id=set_id or 0,
            track_id=track_id,
            position=0,
            name=name,
            cue_type=cue_type or "cue",
            start_sec=start_sec,
            hot_cue_num=slot if slot is not None else -1,
        )
        session.add(cue)
        session.commit()

        return _build_cue_list(session, set_id, track_id), ""

    # --- Set selector options ---
    @app.callback(
        Output("set-selector", "options"),
        Input("set-selector", "search_value"),
    )
    def update_set_options(search):
        session = get_session()
        q = session.query(Set).order_by(Set.created_at.desc())
        if search and len(search) >= 2:
            q = q.filter(Set.name.ilike(f"%{search}%"))
        sets = q.limit(20).all()
        return [
            {"label": f"{s.name} ({len(s.tracks)} tracks)", "value": s.id}
            for s in sets
        ]

    # --- Set selection: load timeline ---
    @app.callback(
        [
            Output("timeline-graph", "figure"),
            Output("current-set-id", "data"),
            Output("transition-label", "children"),
            Output("selected-transition", "data"),
        ],
        Input("set-selector", "value"),
    )
    def load_set_timeline(set_id):
        if not set_id:
            return no_update, no_update, no_update, no_update

        session = get_session()
        set_ = session.query(Set).get(set_id)
        if not set_:
            return no_update, no_update, no_update, no_update

        # Parse energy profile if stored
        energy_profile = None
        if set_.energy_profile:
            try:
                from djsetbuilder.setbuilder.constraints import parse_energy_string
                energy_profile = parse_energy_string(set_.energy_profile)
            except Exception:
                pass

        timeline_fig = build_set_timeline_figure(set_.tracks, energy_profile=energy_profile)

        # Default to first transition
        tracks_sorted = sorted(set_.tracks, key=lambda s: s.position)
        if len(tracks_sorted) >= 2:
            label = f"Track {tracks_sorted[0].position} → {tracks_sorted[1].position}"
            return timeline_fig, set_id, label, 0
        return timeline_fig, set_id, "No transitions", None

    # --- Transition navigation ---
    @app.callback(
        [
            Output("transition-graph", "figure"),
            Output("transition-label", "children", allow_duplicate=True),
            Output("selected-transition", "data", allow_duplicate=True),
            Output("set-cue-list", "children"),
        ],
        [
            Input("btn-prev-transition", "n_clicks"),
            Input("btn-next-transition", "n_clicks"),
            Input("set-selector", "value"),
        ],
        [
            State("selected-transition", "data"),
            State("current-set-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def navigate_transition(prev_clicks, next_clicks, set_value, current_idx, set_id):
        if not set_id:
            return no_update, no_update, no_update, no_update

        session = get_session()
        set_ = session.query(Set).get(set_id)
        if not set_ or len(set_.tracks) < 2:
            return no_update, "No transitions", None, no_update

        tracks_sorted = sorted(set_.tracks, key=lambda s: s.position)
        n_transitions = len(tracks_sorted) - 1

        idx = current_idx or 0
        triggered = callback_context.triggered_id
        if triggered == "btn-next-transition":
            idx = min(idx + 1, n_transitions - 1)
        elif triggered == "btn-prev-transition":
            idx = max(idx - 1, 0)
        elif triggered == "set-selector":
            idx = 0

        st_a = tracks_sorted[idx]
        st_b = tracks_sorted[idx + 1]
        track_a, track_b = st_a.track, st_b.track

        cues_a = _get_cue_dicts(session, set_id, track_a.id)
        cues_b = _get_cue_dicts(session, set_id, track_b.id)

        fig = build_transition_figure(
            track_a, track_a.audio_features,
            track_b, track_b.audio_features,
            cues_a=cues_a, cues_b=cues_b,
        )

        label = (
            f"Track {st_a.position}: {track_a.title or '?'} → "
            f"Track {st_b.position}: {track_b.title or '?'} "
            f"(Score: {st_b.transition_score:.2f})" if st_b.transition_score else
            f"Track {st_a.position} → Track {st_b.position}"
        )

        # Cue list for both tracks at this transition
        cue_html = _build_transition_cue_list(session, set_id, track_a.id, track_b.id)

        return fig, label, idx, cue_html

    # --- Export to Rekordbox ---
    @app.callback(
        Output("export-status", "children"),
        Input("btn-export", "n_clicks"),
        State("current-set-id", "data"),
        prevent_initial_call=True,
    )
    def export_set(n_clicks, set_id):
        if not set_id:
            return html.Div("No set selected.", style={"color": "#f39c12"})

        session = get_session()
        set_ = session.query(Set).get(set_id)
        if not set_:
            return html.Div("Set not found.", style={"color": "#e74c3c"})

        try:
            from djsetbuilder.export.rekordbox_xml import export_set_to_xml
            cues = _get_all_set_cues(session, set_id)
            output_path = export_set_to_xml(set_, transition_cues=cues)
            return html.Div([
                html.Span("Exported: ", style={"color": "#2ecc71", "fontWeight": "600"}),
                html.Code(output_path, style={"color": "#00d2ff"}),
            ])
        except Exception as e:
            return html.Div(f"Export error: {e}", style={"color": "#e74c3c"})

    # --- Compare track ---
    @app.callback(
        [
            Output("compare-panel", "style"),
            Output("compare-graph", "figure"),
        ],
        Input("btn-compare", "n_clicks"),
        [State("current-track-id", "data")],
        prevent_initial_call=True,
    )
    def toggle_compare(n_clicks, track_id):
        if not n_clicks or n_clicks % 2 == 0:
            return {"display": "none"}, no_update
        return {"display": "block"}, no_update

    @app.callback(
        Output("compare-graph", "figure", allow_duplicate=True),
        Input("compare-track-selector", "value"),
        prevent_initial_call=True,
    )
    def load_compare_track(compare_id):
        if not compare_id:
            return no_update

        session = get_session()
        track = session.query(Track).get(compare_id)
        if not track or not track.audio_features:
            return no_update

        return build_track_figure(track, track.audio_features, use_detail=True)

    @app.callback(
        Output("compare-track-selector", "options"),
        Input("compare-track-selector", "search_value"),
    )
    def update_compare_options(search):
        session = get_session()
        if search and len(search) >= 2:
            tracks = search_tracks(session, title=search)
        else:
            tracks = (
                session.query(Track)
                .join(AudioFeatures)
                .filter(AudioFeatures.waveform_overview.isnot(None))
                .order_by(Track.title)
                .limit(50)
                .all()
            )
        return [
            {
                "label": f"{t.title or '?'} — {t.artist or '?'}",
                "value": t.id,
            }
            for t in tracks
        ]


def _get_cue_dicts(session, set_id: int | None, track_id: int) -> list[dict]:
    """Get cue points as dicts for figure rendering."""
    q = session.query(TransitionCue).filter(TransitionCue.track_id == track_id)
    if set_id:
        q = q.filter(TransitionCue.set_id == set_id)
    cues = q.order_by(TransitionCue.start_sec).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "cue_type": c.cue_type,
            "start_sec": c.start_sec,
            "end_sec": c.end_sec,
            "hot_cue_num": c.hot_cue_num,
            "color": c.color,
        }
        for c in cues
    ]


def _build_cue_list(session, set_id: int | None, track_id: int) -> html.Div:
    """Build the cue point list HTML."""
    cues = _get_cue_dicts(session, set_id, track_id)
    if not cues:
        return html.Div("No cue points. Click on the waveform to add one.",
                         style={"color": "#8892b0", "fontSize": "0.85rem"})

    rows = []
    for c in cues:
        minutes = int(c["start_sec"] // 60)
        seconds = c["start_sec"] % 60
        slot = chr(65 + c["hot_cue_num"]) if c["hot_cue_num"] >= 0 else "Mem"
        rows.append(html.Tr([
            html.Td(c["name"]),
            html.Td(c["cue_type"]),
            html.Td(f"{minutes}:{seconds:05.2f}"),
            html.Td(slot),
        ]))

    return html.Table([
        html.Thead(html.Tr([
            html.Th("Name"), html.Th("Type"), html.Th("Time"), html.Th("Slot"),
        ])),
        html.Tbody(rows),
    ], className="cue-list-table")


def _build_transition_cue_list(session, set_id: int, track_a_id: int, track_b_id: int) -> html.Div:
    """Build cue list for a transition pair."""
    cues_a = _get_cue_dicts(session, set_id, track_a_id)
    cues_b = _get_cue_dicts(session, set_id, track_b_id)

    parts = []
    if cues_a:
        parts.append(html.Div([
            html.Span("Track A cues:", style={"color": "#00d2ff", "fontWeight": "600"}),
            _build_cue_list(session, set_id, track_a_id),
        ]))
    if cues_b:
        parts.append(html.Div([
            html.Span("Track B cues:", style={"color": "#e94560", "fontWeight": "600"}),
            _build_cue_list(session, set_id, track_b_id),
        ]))

    if not parts:
        return html.Div("No cue points for this transition.", style={"color": "#8892b0"})
    return html.Div(parts)


def _get_all_set_cues(session, set_id: int) -> dict[int, list[dict]]:
    """Get all cues for a set, organized by track_id for export."""
    cues = (
        session.query(TransitionCue)
        .filter(TransitionCue.set_id == set_id)
        .order_by(TransitionCue.track_id, TransitionCue.start_sec)
        .all()
    )
    result: dict[int, list[dict]] = {}
    for c in cues:
        if c.track_id not in result:
            result[c.track_id] = []
        result[c.track_id].append({
            "name": c.name,
            "type": c.cue_type,
            "start": c.start_sec,
            "end": c.end_sec,
            "num": c.hot_cue_num,
        })
    return result
