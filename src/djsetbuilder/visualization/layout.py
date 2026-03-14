"""Dash layout components for the waveform visualizer."""

from __future__ import annotations

from dash import dcc, html


def build_main_layout() -> html.Div:
    """Build the main application layout."""
    return html.Div([
        # Header
        html.Div([
            html.H1("DJ Set Builder"),
            html.Span("Waveform Visualizer", className="subtitle"),
        ], className="app-header"),

        # Hidden stores for state
        dcc.Store(id="current-track-id", data=None),
        dcc.Store(id="current-set-id", data=None),
        dcc.Store(id="selected-transition", data=None),

        # Tab navigation
        dcc.Tabs(id="main-tabs", value="track-tab", children=[
            dcc.Tab(label="Track View", value="track-tab", style=_tab_style(), selected_style=_tab_selected()),
            dcc.Tab(label="Set Timeline", value="set-tab", style=_tab_style(), selected_style=_tab_selected()),
        ], style={"marginTop": "8px"}),

        # Tab content
        html.Div(id="tab-content", style={"padding": "8px"}),
    ])


def build_track_tab() -> html.Div:
    """Build the single track view tab."""
    return html.Div([
        # Track selector
        html.Div([
            html.Div("Track Selector", className="panel-title"),
            html.Div([
                dcc.Dropdown(
                    id="track-selector",
                    placeholder="Search tracks...",
                    style={"flex": 1, "backgroundColor": "#16213e", "color": "#e0e0e0"},
                ),
                html.Button("Compare", id="btn-compare", className="btn btn-secondary",
                            style={"marginLeft": "8px"}),
            ], style={"display": "flex", "alignItems": "center"}),
        ], className="panel"),

        # Track info bar
        html.Div(id="track-info", className="panel", style={"display": "none"}),

        # Overview waveform
        html.Div([
            html.Div("Overview", className="panel-title"),
            dcc.Graph(id="overview-graph", config={"displayModeBar": False}, style={"height": "80px"}),
        ], className="panel"),

        # Detail waveform
        html.Div([
            html.Div("Detail", className="panel-title"),
            dcc.Graph(id="detail-graph", config={"scrollZoom": True}),
        ], className="panel"),

        # Cue points panel
        html.Div([
            html.Div("Cue Points", className="panel-title"),
            html.Div(id="cue-list"),
            html.Div([
                dcc.Input(id="cue-name-input", placeholder="Cue name", type="text",
                          style={"backgroundColor": "#0f3460", "color": "#e0e0e0",
                                 "border": "1px solid #2a2a4a", "padding": "6px", "borderRadius": "4px"}),
                dcc.Dropdown(
                    id="cue-type-selector",
                    options=[
                        {"label": "Cue", "value": "cue"},
                        {"label": "Loop", "value": "loop"},
                        {"label": "Fade In", "value": "fadein"},
                        {"label": "Fade Out", "value": "fadeout"},
                    ],
                    value="cue",
                    style={"width": "120px", "backgroundColor": "#16213e"},
                ),
                dcc.Dropdown(
                    id="cue-slot-selector",
                    options=[{"label": "Memory", "value": -1}]
                            + [{"label": chr(65 + i), "value": i} for i in range(8)],
                    value=-1,
                    style={"width": "100px", "backgroundColor": "#16213e"},
                ),
                html.Div(id="cue-click-info", style={"color": "#8892b0", "fontSize": "0.85rem",
                                                       "padding": "6px"}),
            ], style={"display": "flex", "gap": "8px", "alignItems": "center", "marginTop": "8px"}),
        ], className="panel"),

        # Compare panel (hidden by default)
        html.Div(id="compare-panel", style={"display": "none"}, children=[
            html.Div([
                html.Div("Compare Track", className="panel-title"),
                dcc.Dropdown(id="compare-track-selector", placeholder="Select track to compare...",
                             style={"backgroundColor": "#16213e"}),
                dcc.Graph(id="compare-graph"),
            ], className="panel"),
        ]),
    ])


def build_set_tab() -> html.Div:
    """Build the set timeline tab."""
    return html.Div([
        # Set selector
        html.Div([
            html.Div("Set Selector", className="panel-title"),
            html.Div([
                dcc.Dropdown(
                    id="set-selector",
                    placeholder="Select a set...",
                    style={"flex": 1, "backgroundColor": "#16213e"},
                ),
                html.Button("Export to Rekordbox", id="btn-export", className="btn btn-primary",
                            style={"marginLeft": "8px"}),
            ], style={"display": "flex", "alignItems": "center"}),
        ], className="panel"),

        # View toggle + Set timeline
        html.Div([
            html.Div([
                html.Div("Timeline", className="panel-title", style={"flex": 1}),
                dcc.RadioItems(
                    id="timeline-view-toggle",
                    options=[
                        {"label": "Linear", "value": "linear"},
                        {"label": "Staircase", "value": "staircase"},
                    ],
                    value="linear",
                    inline=True,
                    style={"color": "#e0e0e0", "fontSize": "0.85rem"},
                    inputStyle={"marginRight": "4px"},
                    labelStyle={"marginRight": "12px"},
                ),
            ], style={"display": "flex", "alignItems": "center"}),
            dcc.Graph(id="timeline-graph", config={"scrollZoom": True}),

            # Track nudge controls (visible in staircase mode after clicking a track)
            html.Div(id="track-nudge-panel", style={"display": "none"}, children=[
                html.Div([
                    html.Span(id="nudge-track-label", style={"color": "#e0e0e0", "fontWeight": "600",
                                                               "marginRight": "12px", "minWidth": "200px"}),
                    html.Button("-8 beats", id="btn-nudge-left-big", className="btn btn-secondary",
                                style={"fontSize": "0.8rem", "padding": "4px 8px"}),
                    html.Button("-1 beat", id="btn-nudge-left", className="btn btn-secondary",
                                style={"fontSize": "0.8rem", "padding": "4px 8px", "marginLeft": "4px"}),
                    dcc.Input(id="nudge-offset-display", type="text", readOnly=True,
                              style={"width": "80px", "textAlign": "center", "margin": "0 8px",
                                     "backgroundColor": "#0f3460", "color": "#00d2ff",
                                     "border": "1px solid #2a2a4a", "borderRadius": "4px",
                                     "padding": "4px"}),
                    html.Button("+1 beat", id="btn-nudge-right", className="btn btn-secondary",
                                style={"fontSize": "0.8rem", "padding": "4px 8px"}),
                    html.Button("+8 beats", id="btn-nudge-right-big", className="btn btn-secondary",
                                style={"fontSize": "0.8rem", "padding": "4px 8px", "marginLeft": "4px"}),
                    html.Button("Reset", id="btn-nudge-reset", className="btn btn-secondary",
                                style={"fontSize": "0.8rem", "padding": "4px 8px", "marginLeft": "12px"}),
                    html.Button("Reset All", id="btn-nudge-reset-all", className="btn btn-secondary",
                                style={"fontSize": "0.8rem", "padding": "4px 8px", "marginLeft": "4px"}),
                ], style={"display": "flex", "alignItems": "center", "padding": "8px 0"}),
            ]),
            dcc.Store(id="track-offsets", data={}),
            dcc.Store(id="selected-staircase-track", data=None),
        ], className="panel"),

        # Transition detail
        html.Div([
            html.Div("Transition Detail", className="panel-title"),
            html.Div([
                html.Button("< Prev", id="btn-prev-transition", className="btn btn-secondary"),
                html.Span(id="transition-label", style={"padding": "0 16px", "color": "#e0e0e0"}),
                html.Button("Next >", id="btn-next-transition", className="btn btn-secondary"),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px"}),
            dcc.Graph(id="transition-graph", config={"scrollZoom": True}),

            # Audio players
            html.Div([
                html.Div([
                    html.Div([
                        html.Span("A: ", style={"color": "#00d2ff", "fontWeight": "600"}),
                        html.Span(id="player-a-label", style={"color": "#e0e0e0"}),
                    ], style={"marginBottom": "4px"}),
                    html.Audio(id="audio-player-a", controls=True,
                               style={"width": "100%"}),
                ], style={"flex": 1}),
                html.Div([
                    html.Div([
                        html.Span("B: ", style={"color": "#e94560", "fontWeight": "600"}),
                        html.Span(id="player-b-label", style={"color": "#e0e0e0"}),
                    ], style={"marginBottom": "4px"}),
                    html.Audio(id="audio-player-b", controls=True,
                               style={"width": "100%"}),
                ], style={"flex": 1}),
            ], style={"display": "flex", "gap": "16px", "padding": "8px 0"}),

            html.Div([
                html.Button("Play Both", id="btn-play-both", className="btn btn-primary",
                            style={"fontSize": "0.85rem", "padding": "6px 16px"}),
                html.Button("Stop Both", id="btn-stop-both", className="btn btn-secondary",
                            style={"fontSize": "0.85rem", "padding": "6px 16px", "marginLeft": "8px"}),
                html.Button("Reset A", id="btn-reset-a", className="btn btn-secondary",
                            title="Seek player A back to start of section",
                            style={"fontSize": "0.85rem", "padding": "6px 16px", "marginLeft": "8px",
                                   "borderColor": "#00d2ff", "color": "#00d2ff"}),
            ], style={"display": "flex", "alignItems": "center", "padding": "4px 0"}),

            dcc.Store(id="player-state", data=None),
            dcc.Interval(id="playhead-interval", interval=200, disabled=True),

            # Track B nudge controls
            html.Div([
                html.Span("Move Track B:", style={"color": "#e94560", "fontWeight": "600",
                                                    "marginRight": "12px"}),
                html.Button("-8 beats", id="btn-trans-nudge-left-big", className="btn btn-secondary",
                            style={"fontSize": "0.8rem", "padding": "4px 8px"}),
                html.Button("-1 beat", id="btn-trans-nudge-left", className="btn btn-secondary",
                            style={"fontSize": "0.8rem", "padding": "4px 8px", "marginLeft": "4px"}),
                dcc.Input(id="trans-nudge-display", type="text", readOnly=True, value="+0.0s",
                          style={"width": "80px", "textAlign": "center", "margin": "0 8px",
                                 "backgroundColor": "#0f3460", "color": "#e94560",
                                 "border": "1px solid #2a2a4a", "borderRadius": "4px",
                                 "padding": "4px"}),
                html.Button("+1 beat", id="btn-trans-nudge-right", className="btn btn-secondary",
                            style={"fontSize": "0.8rem", "padding": "4px 8px"}),
                html.Button("+8 beats", id="btn-trans-nudge-right-big", className="btn btn-secondary",
                            style={"fontSize": "0.8rem", "padding": "4px 8px", "marginLeft": "4px"}),
                html.Button("Reset", id="btn-trans-nudge-reset", className="btn btn-secondary",
                            style={"fontSize": "0.8rem", "padding": "4px 8px", "marginLeft": "12px"}),
            ], style={"display": "flex", "alignItems": "center", "padding": "8px 0"}),
            dcc.Store(id="transition-b-offsets", data={}),
        ], className="panel"),

        # Set cue points
        html.Div([
            html.Div("Set Cue Points", className="panel-title"),
            html.Div(id="set-cue-list"),
        ], className="panel"),

        # Export status
        html.Div(id="export-status", style={"padding": "8px"}),
    ])


def _tab_style() -> dict:
    return {
        "backgroundColor": "#1a1a2e",
        "color": "#8892b0",
        "border": "none",
        "borderBottom": "2px solid #2a2a4a",
        "padding": "10px 20px",
    }


def _tab_selected() -> dict:
    return {
        "backgroundColor": "#16213e",
        "color": "#e94560",
        "border": "none",
        "borderBottom": "2px solid #e94560",
        "padding": "10px 20px",
    }
