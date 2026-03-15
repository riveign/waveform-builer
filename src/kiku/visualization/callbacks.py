"""Dash callback handlers for the waveform visualizer."""

from __future__ import annotations

import json

from dash import ClientsideFunction, Input, Output, State, callback_context, html, no_update

from kiku.db.models import AudioFeatures, Set, SetTrack, Track, TransitionCue, get_session
from kiku.db.store import get_track_by_title, search_tracks
from kiku.visualization.figures import (
    build_bpm_histogram,
    build_camelot_bar,
    build_camelot_radar,
    build_energy_genre_heatmap,
    build_mood_scatter,
    build_overview_figure,
    build_set_timeline_figure,
    build_staircase_figure,
    build_track_figure,
    build_transition_figure,
)
from kiku.visualization.layout import build_set_tab, build_track_tab


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
        elif tab == "dna-tab":
            return _build_dna_tab_with_data()
        return html.Div()

    # --- Camelot view toggle ---
    app.clientside_callback(
        """
        function(view) {
            if (view === 'bar') {
                return [{display: 'none'}, {display: 'block'}];
            }
            return [{display: 'block'}, {display: 'none'}];
        }
        """,
        [Output("camelot-wheel-container", "style"),
         Output("camelot-bar-container", "style")],
        Input("camelot-view-toggle", "value"),
        prevent_initial_call=True,
    )

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
        track = session.get(Track, track_id)
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
        [
            Input("set-selector", "value"),
            Input("timeline-view-toggle", "value"),
            Input("track-offsets", "data"),
        ],
    )
    def load_set_timeline(set_id, view_mode, track_offsets):
        if not set_id:
            return no_update, no_update, no_update, no_update

        session = get_session()
        set_ = session.get(Set, set_id)
        if not set_:
            return no_update, no_update, no_update, no_update

        # Parse energy profile if stored
        energy_profile = None
        if set_.energy_profile:
            try:
                from kiku.setbuilder.constraints import parse_energy_json
                energy_profile = parse_energy_json(set_.energy_profile)
            except Exception:
                pass

        if view_mode == "staircase":
            timeline_fig = build_staircase_figure(
                set_.tracks, energy_profile=energy_profile,
                track_offsets=track_offsets or {},
            )
        else:
            timeline_fig = build_set_timeline_figure(set_.tracks, energy_profile=energy_profile)

        # uirevision: keep same value while nudging so Plotly preserves zoom/pan.
        # Changes when set or view mode changes (reset zoom is appropriate then).
        timeline_fig.update_layout(uirevision=f"{set_id}-{view_mode}")

        # Default to first transition
        tracks_sorted = sorted(set_.tracks, key=lambda s: s.position)
        if len(tracks_sorted) >= 2:
            label = f"Track {tracks_sorted[0].position} → {tracks_sorted[1].position}"
            return timeline_fig, set_id, label, 0
        return timeline_fig, set_id, "No transitions", None

    # --- Click on staircase to select a track ---
    @app.callback(
        [
            Output("selected-staircase-track", "data"),
            Output("track-nudge-panel", "style"),
            Output("nudge-track-label", "children"),
            Output("nudge-offset-display", "value"),
        ],
        Input("timeline-graph", "clickData"),
        [
            State("timeline-view-toggle", "value"),
            State("track-offsets", "data"),
            State("current-set-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def select_staircase_track(click_data, view_mode, offsets, set_id):
        if view_mode != "staircase" or not click_data:
            return no_update, {"display": "none"}, "", ""

        points = click_data.get("points", [])
        if not points:
            return no_update, {"display": "none"}, "", ""

        # Each track has 2 traces (waveform line + fill area), so track_idx = curve // 2
        curve = points[0].get("curveNumber", 0)
        track_idx = curve // 2

        # Resolve actual track info from set
        session = get_session()
        set_ = session.get(Set, set_id) if set_id else None
        if not set_:
            return no_update, {"display": "none"}, "", ""

        tracks_sorted = sorted(set_.tracks, key=lambda s: s.position)
        if track_idx >= len(tracks_sorted):
            return no_update, {"display": "none"}, "", ""

        st = tracks_sorted[track_idx]
        offsets = offsets or {}
        current_offset = offsets.get(str(st.position), 0)

        return (
            track_idx,
            {"display": "block"},
            f"{st.position}. {st.track.title or '?'} ({st.track.bpm:.0f} BPM)" if st.track.bpm else f"{st.position}. {st.track.title or '?'}",
            f"{current_offset:+.1f}s",
        )

    # --- Nudge track offset ---
    @app.callback(
        [
            Output("track-offsets", "data"),
            Output("nudge-offset-display", "value", allow_duplicate=True),
        ],
        [
            Input("btn-nudge-left-big", "n_clicks"),
            Input("btn-nudge-left", "n_clicks"),
            Input("btn-nudge-right", "n_clicks"),
            Input("btn-nudge-right-big", "n_clicks"),
            Input("btn-nudge-reset", "n_clicks"),
            Input("btn-nudge-reset-all", "n_clicks"),
        ],
        [
            State("selected-staircase-track", "data"),
            State("track-offsets", "data"),
            State("current-set-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def nudge_track(left_big, left, right, right_big, reset, reset_all,
                    track_idx, offsets, set_id):
        if track_idx is None:
            return no_update, no_update

        offsets = dict(offsets or {})
        triggered = callback_context.triggered_id

        if triggered == "btn-nudge-reset-all":
            return {}, "+0.0s"

        # Get BPM for beat-based nudge
        session = get_session()
        set_ = session.get(Set, set_id) if set_id else None
        bpm = 120
        if set_:
            tracks_sorted = sorted(set_.tracks, key=lambda s: s.position)
            if track_idx < len(tracks_sorted):
                bpm = tracks_sorted[track_idx].track.bpm or 120

        beat_sec = 60 / bpm  # 1 beat in seconds
        pos_key = str(tracks_sorted[track_idx].position) if set_ and track_idx < len(tracks_sorted) else str(track_idx)
        current = offsets.get(pos_key, 0)

        if triggered == "btn-nudge-reset":
            offsets[pos_key] = 0
        elif triggered == "btn-nudge-left-big":
            offsets[pos_key] = current - beat_sec * 8
        elif triggered == "btn-nudge-left":
            offsets[pos_key] = current - beat_sec
        elif triggered == "btn-nudge-right":
            offsets[pos_key] = current + beat_sec
        elif triggered == "btn-nudge-right-big":
            offsets[pos_key] = current + beat_sec * 8

        new_offset = offsets.get(pos_key, 0)
        return offsets, f"{new_offset:+.1f}s"

    # --- Transition B-track nudge ---
    @app.callback(
        [
            Output("transition-b-offsets", "data"),
            Output("trans-nudge-display", "value"),
        ],
        [
            Input("btn-trans-nudge-left-big", "n_clicks"),
            Input("btn-trans-nudge-left", "n_clicks"),
            Input("btn-trans-nudge-right", "n_clicks"),
            Input("btn-trans-nudge-right-big", "n_clicks"),
            Input("btn-trans-nudge-reset", "n_clicks"),
        ],
        [
            State("transition-b-offsets", "data"),
            State("selected-transition", "data"),
            State("current-set-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def nudge_transition_b(left_big, left, right, right_big, reset,
                           offsets, current_idx, set_id):
        if current_idx is None or not set_id:
            return no_update, no_update

        offsets = dict(offsets or {})
        triggered = callback_context.triggered_id

        # Get target BPM for beat-based nudge
        session = get_session()
        set_ = session.get(Set, set_id)
        if not set_ or len(set_.tracks) < 2:
            return no_update, no_update

        tracks_sorted = sorted(set_.tracks, key=lambda s: s.position)
        if current_idx + 1 >= len(tracks_sorted):
            return no_update, no_update

        bpm_a = tracks_sorted[current_idx].track.bpm or 120
        bpm_b = tracks_sorted[current_idx + 1].track.bpm or 120
        target_bpm = (bpm_a + bpm_b) / 2
        beat_sec = 60 / target_bpm

        key = str(current_idx)
        current = offsets.get(key, 0)

        if triggered == "btn-trans-nudge-reset":
            offsets[key] = 0
        elif triggered == "btn-trans-nudge-left-big":
            offsets[key] = current - beat_sec * 8
        elif triggered == "btn-trans-nudge-left":
            offsets[key] = current - beat_sec
        elif triggered == "btn-trans-nudge-right":
            offsets[key] = current + beat_sec
        elif triggered == "btn-trans-nudge-right-big":
            offsets[key] = current + beat_sec * 8

        new_offset = offsets.get(key, 0)
        return offsets, f"{new_offset:+.1f}s"

    # --- Transition navigation ---
    @app.callback(
        [
            Output("transition-graph", "figure"),
            Output("transition-label", "children", allow_duplicate=True),
            Output("selected-transition", "data", allow_duplicate=True),
            Output("set-cue-list", "children"),
            Output("player-state", "data"),
            Output("player-a-label", "children"),
            Output("player-b-label", "children"),
        ],
        [
            Input("btn-prev-transition", "n_clicks"),
            Input("btn-next-transition", "n_clicks"),
            Input("set-selector", "value"),
            Input("transition-b-offsets", "data"),
        ],
        [
            State("selected-transition", "data"),
            State("current-set-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def navigate_transition(prev_clicks, next_clicks, set_value, b_offsets, current_idx, set_id):
        if not set_id:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

        session = get_session()
        set_ = session.get(Set, set_id)
        if not set_ or len(set_.tracks) < 2:
            return no_update, "No transitions", None, no_update, None, "", ""

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

        b_offsets = b_offsets or {}
        b_offset = b_offsets.get(str(idx), 0)

        fig = build_transition_figure(
            track_a, track_a.audio_features,
            track_b, track_b.audio_features,
            cues_a=cues_a, cues_b=cues_b,
            b_offset=b_offset,
        )

        label = (
            f"Track {st_a.position}: {track_a.title or '?'} → "
            f"Track {st_b.position}: {track_b.title or '?'} "
            f"(Score: {st_b.transition_score:.2f})" if st_b.transition_score else
            f"Track {st_a.position} → Track {st_b.position}"
        )

        # Cue list for both tracks at this transition
        cue_html = _build_transition_cue_list(session, set_id, track_a.id, track_b.id)

        # Compute player-state for audio positioning
        from kiku.visualization.figures import _compute_transition_timeline
        af_a, af_b = track_a.audio_features, track_b.audio_features
        overlap_seconds = 30.0
        view_window = overlap_seconds * 2
        tl = _compute_transition_timeline(
            af_a, af_b, track_a, track_b,
            overlap_seconds, b_offset, view_window,
        )
        (_mapped_a, _mask_a, show_from_raw_a, _a_end_time,
         _mapped_b, _mask_b, _show_until_raw_b, b_start_on_timeline,
         scale_a, scale_b, _target_bpm) = tl

        player_state = {
            "track_a_id": track_a.id,
            "track_b_id": track_b.id,
            "start_a": show_from_raw_a or 0,
            "start_b": 0,
            "scale_a": scale_a,
            "scale_b": scale_b,
            "b_start_on_timeline": b_start_on_timeline,
        }

        label_a = f"{track_a.title or '?'} — {track_a.artist or '?'}"
        label_b = f"{track_b.title or '?'} — {track_b.artist or '?'}"

        return fig, label, idx, cue_html, player_state, label_a, label_b

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
        set_ = session.get(Set, set_id)
        if not set_:
            return html.Div("Set not found.", style={"color": "#e74c3c"})

        try:
            from kiku.export.rekordbox_xml import export_set_to_xml
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
        track = session.get(Track, compare_id)
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

    # --- Clientside: load audio sources from player-state ---
    # Re-seeks both players whenever player-state changes (new transition OR nudge).
    app.clientside_callback(
        """
        function(playerState) {
            if (!playerState) return [null, null];
            var audioA = document.getElementById('audio-player-a');
            var audioB = document.getElementById('audio-player-b');
            var srcA = '/audio/' + playerState.track_a_id;
            var srcB = '/audio/' + playerState.track_b_id;

            if (audioA) {
                var newTrackA = (audioA.src !== location.origin + srcA);
                if (newTrackA) {
                    audioA.src = srcA;
                    audioA.addEventListener('canplay', function onCanPlay() {
                        audioA.currentTime = playerState.start_a;
                        audioA.removeEventListener('canplay', onCanPlay);
                    });
                } else {
                    // Same track, just re-seek (nudge changed the view)
                    audioA.currentTime = playerState.start_a;
                }
            }
            if (audioB) {
                var newTrackB = (audioB.src !== location.origin + srcB);
                if (newTrackB) {
                    audioB.src = srcB;
                    audioB.addEventListener('canplay', function onCanPlay() {
                        audioB.currentTime = playerState.start_b;
                        audioB.removeEventListener('canplay', onCanPlay);
                    });
                } else {
                    audioB.currentTime = playerState.start_b;
                }
            }
            return [srcA, srcB];
        }
        """,
        [Output("audio-player-a", "src"), Output("audio-player-b", "src")],
        Input("player-state", "data"),
        prevent_initial_call=True,
    )

    # --- Clientside: Play Both / Stop Both / Reset A ---
    app.clientside_callback(
        """
        function(playClicks, stopClicks, resetAClicks, playerState) {
            var triggered = dash_clientside.callback_context.triggered;
            if (!triggered || triggered.length === 0) return true;
            var triggeredId = triggered[0].prop_id.split('.')[0];

            var audioA = document.getElementById('audio-player-a');
            var audioB = document.getElementById('audio-player-b');

            if (triggeredId === 'btn-play-both') {
                if (audioA && audioA.src) audioA.play();
                if (audioB && audioB.src) audioB.play();
                return false;
            } else if (triggeredId === 'btn-stop-both') {
                if (audioA) audioA.pause();
                if (audioB) audioB.pause();
                return true;
            } else if (triggeredId === 'btn-reset-a') {
                if (audioA && playerState) {
                    audioA.currentTime = playerState.start_a;
                }
                // Keep interval in current state
                return dash_clientside.no_update;
            }
            return true;
        }
        """,
        Output("playhead-interval", "disabled"),
        [
            Input("btn-play-both", "n_clicks"),
            Input("btn-stop-both", "n_clicks"),
            Input("btn-reset-a", "n_clicks"),
        ],
        State("player-state", "data"),
        prevent_initial_call=True,
    )

    # --- Clientside: playhead tick → inject vertical line shapes ---
    app.clientside_callback(
        """
        function(nIntervals, figure, playerState) {
            if (!figure || !playerState) return dash_clientside.no_update;

            var audioA = document.getElementById('audio-player-a');
            var audioB = document.getElementById('audio-player-b');
            if (!audioA && !audioB) return dash_clientside.no_update;

            var newFig = Object.assign({}, figure);
            var layout = Object.assign({}, newFig.layout || {});

            // Preserve existing shapes (overlap zones, markers) — filter out old playheads
            var existingShapes = (layout.shapes || []).filter(function(s) {
                return !s._playhead;
            });
            var playheadShapes = [];

            if (audioA && audioA.src && !audioA.paused) {
                var tA = audioA.currentTime;
                var xA = (tA - playerState.start_a) * playerState.scale_a;
                playheadShapes.push({
                    type: 'line', _playhead: true,
                    x0: xA, x1: xA, y0: 0, y1: 1,
                    xref: 'x', yref: 'paper',
                    line: {color: '#00d2ff', width: 2}
                });
            }
            if (audioB && audioB.src && !audioB.paused) {
                var tB = audioB.currentTime;
                var xB = tB * playerState.scale_b + playerState.b_start_on_timeline;
                playheadShapes.push({
                    type: 'line', _playhead: true,
                    x0: xB, x1: xB, y0: 0, y1: 1,
                    xref: 'x', yref: 'paper',
                    line: {color: '#e94560', width: 2}
                });
            }

            layout.shapes = existingShapes.concat(playheadShapes);
            newFig.layout = layout;
            return newFig;
        }
        """,
        Output("transition-graph", "figure", allow_duplicate=True),
        Input("playhead-interval", "n_intervals"),
        [State("transition-graph", "figure"), State("player-state", "data")],
        prevent_initial_call=True,
    )


def _build_dna_tab_with_data():
    """Build the DNA tab with pre-computed figures baked into the layout."""
    from dash import dcc, html

    from kiku.analysis.insights import (
        bpm_histogram as bpm_hist_data,
        camelot_distribution,
        energy_genre_heatmap as heatmap_data,
        mood_quadrant,
    )

    session = get_session()
    cam_data = camelot_distribution(session)
    wheel_fig = build_camelot_radar(cam_data)
    bar_fig = build_camelot_bar(cam_data)
    bpm_fig = build_bpm_histogram(bpm_hist_data(session))
    heatmap_fig = build_energy_genre_heatmap(heatmap_data(session))
    mood_fig = build_mood_scatter(mood_quadrant(session))

    graph_style = {"height": "400px"}
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.Span("Key Distribution", className="panel-title", style={"flex": 1}),
                    dcc.RadioItems(
                        id="camelot-view-toggle",
                        options=[
                            {"label": "Wheel", "value": "wheel"},
                            {"label": "Bar", "value": "bar"},
                        ],
                        value="wheel",
                        inline=True,
                        style={"color": "#e0e0e0", "fontSize": "0.85rem"},
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "12px"},
                    ),
                ], style={"display": "flex", "alignItems": "center"}),
                html.Div(id="camelot-wheel-container",
                         children=dcc.Graph(figure=wheel_fig, config={"displayModeBar": False}, style=graph_style)),
                html.Div(id="camelot-bar-container", style={"display": "none"},
                         children=dcc.Graph(figure=bar_fig, config={"displayModeBar": False}, style=graph_style)),
            ], className="panel", style={"flex": 1}),
            html.Div([
                html.Div("BPM Distribution", className="panel-title"),
                dcc.Graph(figure=bpm_fig, config={"displayModeBar": False}, style=graph_style),
            ], className="panel", style={"flex": 1}),
        ], style={"display": "flex", "gap": "8px"}),
        html.Div([
            html.Div([
                html.Div("Energy x Genre", className="panel-title"),
                dcc.Graph(figure=heatmap_fig, config={"displayModeBar": False}, style=graph_style),
            ], className="panel", style={"flex": 1}),
            html.Div([
                html.Div("Mood Quadrant", className="panel-title"),
                dcc.Graph(figure=mood_fig, config={"displayModeBar": False}, style=graph_style),
            ], className="panel", style={"flex": 1}),
        ], style={"display": "flex", "gap": "8px"}),
    ])


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
