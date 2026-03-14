"""Plotly figure builders for waveform and library visualization."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from djsetbuilder.analysis.waveform import envelope_to_time_axis

# Genre family color map (shared across Taste DNA charts)
FAMILY_COLORS: dict[str, str] = {
    "Techno": "#00d2ff",
    "House": "#e94560",
    "Groove": "#2ecc71",
    "Trance": "#f39c12",
    "Breaks": "#9b59b6",
    "Electronic": "#1abc9c",
    "Other": "#8892b0",
}

# Cue type colors
CUE_COLORS = {
    "cue": "#00d2ff",
    "loop": "#2ecc71",
    "fadein": "#f1c40f",
    "fadeout": "#e74c3c",
}

DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#16213e",
    plot_bgcolor="#0f3460",
    font=dict(color="#e0e0e0", size=11),
    margin=dict(l=40, r=20, t=30, b=40),
    xaxis=dict(gridcolor="#2a2a4a", zerolinecolor="#2a2a4a"),
    yaxis=dict(gridcolor="#2a2a4a", zerolinecolor="#2a2a4a"),
)


def _load_waveform(audio_features, use_detail: bool = False) -> tuple[np.ndarray, np.ndarray] | None:
    """Load waveform data from AudioFeatures, return (time_axis, envelope)."""
    blob = audio_features.waveform_detail if use_detail else audio_features.waveform_overview
    if blob is None:
        return None

    envelope = np.frombuffer(blob, dtype=np.float32)
    sr = audio_features.waveform_sr or 22050
    hop = audio_features.waveform_hop or 512

    if use_detail:
        time_axis = envelope_to_time_axis(len(envelope), sr, hop)
    else:
        # Overview: evenly space across track duration
        duration = len(np.frombuffer(audio_features.waveform_detail, dtype=np.float32)) * hop / sr if audio_features.waveform_detail else len(envelope)
        time_axis = np.linspace(0, duration, len(envelope))

    return time_axis, envelope


# Frequency band display config: (column_name, label, color)
BAND_CONFIG = [
    ("band_low", "Low (20–250 Hz)", "#e74c3c"),
    ("band_midlow", "Mid-low (250–1k Hz)", "#f39c12"),
    ("band_midhigh", "Mid-high (1k–4k Hz)", "#2ecc71"),
    ("band_high", "High (4k–11k Hz)", "#00d2ff"),
]


def _load_band_envelopes(
    audio_features, use_detail: bool = False,
) -> dict[str, np.ndarray] | None:
    """Load per-band RMS envelopes from AudioFeatures.

    Returns dict mapping band column name to float32 array, or None if
    band data is not available.
    """
    suffix = "" if use_detail else "_overview"
    bands = {}
    for col_name, _label, _color in BAND_CONFIG:
        blob = getattr(audio_features, f"{col_name}{suffix}", None)
        if blob is None:
            return None
        bands[col_name] = np.frombuffer(blob, dtype=np.float32)
    return bands


def _load_beats(audio_features) -> np.ndarray | None:
    """Load beat positions from AudioFeatures."""
    if audio_features.beat_positions is None:
        return None
    return np.frombuffer(audio_features.beat_positions, dtype=np.float32)


def build_track_figure(
    track,
    audio_features,
    show_beats: bool = True,
    show_energy: bool = True,
    cue_points: list | None = None,
    use_detail: bool = False,
) -> go.Figure:
    """Build an interactive waveform figure for a single track."""
    fig = go.Figure()

    waveform_data = _load_waveform(audio_features, use_detail=use_detail)
    if waveform_data is None:
        fig.add_annotation(text="No waveform data. Run: djset analyze --waveform-only",
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                          font=dict(size=16, color="#e94560"))
        fig.update_layout(**DARK_LAYOUT)
        return fig

    time_axis, envelope = waveform_data

    # Main waveform trace
    fig.add_trace(go.Scattergl(
        x=time_axis,
        y=envelope,
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(0, 210, 255, 0.3)",
        line=dict(color="#00d2ff", width=1),
        name="Waveform",
        hovertemplate="Time: %{x:.1f}s<br>Level: %{y:.3f}<extra></extra>",
    ))

    # Mirror waveform for symmetry
    fig.add_trace(go.Scattergl(
        x=time_axis,
        y=-envelope,
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(0, 210, 255, 0.15)",
        line=dict(color="#00d2ff", width=1),
        name="Waveform",
        showlegend=False,
        hoverinfo="skip",
    ))

    # Beat markers
    if show_beats:
        beats = _load_beats(audio_features)
        if beats is not None:
            max_env = float(np.max(envelope)) if len(envelope) > 0 else 1.0
            fig.add_trace(go.Scattergl(
                x=beats,
                y=np.full(len(beats), max_env * 1.05),
                mode="markers",
                marker=dict(symbol="line-ns", size=8, color="#533483", line=dict(width=1, color="#533483")),
                name="Beats",
                hovertemplate="Beat: %{x:.2f}s<extra></extra>",
            ))

    # Energy overlay
    if show_energy and audio_features.energy_intro is not None:
        duration = float(time_axis[-1]) if len(time_axis) > 0 else 300
        energy_x = [0, duration * 0.15, duration * 0.15, duration * 0.85, duration * 0.85, duration]
        energy_y = [audio_features.energy_intro] * 2 + [audio_features.energy_body] * 2 + [audio_features.energy_outro] * 2
        fig.add_trace(go.Scatter(
            x=energy_x,
            y=energy_y,
            mode="lines",
            line=dict(color="#e94560", width=2, dash="dash"),
            name="Energy Curve",
            hovertemplate="Energy: %{y:.2f}<extra></extra>",
        ))

    # Cue point markers
    if cue_points:
        add_cue_markers(fig, cue_points, float(np.max(envelope)) if len(envelope) > 0 else 1.0)

    title = f"{track.title or 'Unknown'} — {track.artist or 'Unknown'}"
    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="Time (seconds)",
        yaxis_title="Level",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        dragmode="zoom",
    )

    return fig


def build_overview_figure(track, audio_features) -> go.Figure:
    """Build a compact overview waveform (no beats, no energy, minimal UI)."""
    fig = go.Figure()

    waveform_data = _load_waveform(audio_features, use_detail=False)
    if waveform_data is None:
        fig.update_layout(**DARK_LAYOUT, height=80)
        return fig

    time_axis, envelope = waveform_data

    fig.add_trace(go.Scattergl(
        x=time_axis, y=envelope,
        mode="lines", fill="tozeroy",
        fillcolor="rgba(0, 210, 255, 0.4)",
        line=dict(color="#00d2ff", width=1),
        hoverinfo="skip",
    ))

    fig.update_layout(
        **{**DARK_LAYOUT, "margin": dict(l=0, r=0, t=0, b=0),
           "xaxis": dict(visible=False), "yaxis": dict(visible=False)},
        height=80,
        showlegend=False,
    )

    return fig


def build_set_timeline_figure(
    set_tracks: list,
    energy_profile=None,
    show_transitions: bool = True,
) -> go.Figure:
    """Build a set timeline figure showing all track waveforms end-to-end."""
    fig = go.Figure()

    cumulative_time = 0.0
    track_boundaries = []
    annotations = []

    for st in sorted(set_tracks, key=lambda s: s.position):
        track = st.track
        af = track.audio_features
        duration = track.duration_sec or 300

        if af and af.waveform_overview:
            envelope = np.frombuffer(af.waveform_overview, dtype=np.float32)
            time_axis = np.linspace(cumulative_time, cumulative_time + duration, len(envelope))

            fig.add_trace(go.Scattergl(
                x=time_axis, y=envelope,
                mode="lines", fill="tozeroy",
                fillcolor="rgba(0, 210, 255, 0.3)",
                line=dict(color="#00d2ff", width=1),
                name=f"{st.position}. {track.title or '?'}",
                hovertemplate=(
                    f"<b>{track.title}</b><br>"
                    f"Artist: {track.artist or '?'}<br>"
                    f"BPM: {f'{track.bpm:.0f}' if track.bpm else '?'} | Key: {track.key or '?'}<br>"
                    "Time: %{x:.0f}s<br>Level: %{y:.3f}<extra></extra>"
                ),
            ))

        # Track boundary line
        if cumulative_time > 0:
            fig.add_vline(
                x=cumulative_time, line=dict(color="#e94560", width=1, dash="dot"),
                annotation_text=f"{st.transition_score:.2f}" if st.transition_score and show_transitions else None,
                annotation_font=dict(size=10, color="#e94560"),
            )

        # Track label at center
        annotations.append(dict(
            x=cumulative_time + duration / 2,
            y=1.08,
            xref="x", yref="paper",
            text=f"<b>{st.position}.</b> {track.title or '?'}<br>"
                 f"<span style='font-size:10px'>{f'{track.bpm:.0f}' if track.bpm else '?'} BPM | {track.key or '?'}</span>",
            showarrow=False,
            font=dict(size=11, color="#e0e0e0"),
        ))

        track_boundaries.append((cumulative_time, cumulative_time + duration, st))
        cumulative_time += duration

    # Energy target curve overlay
    if energy_profile is not None:
        try:
            from djsetbuilder.setbuilder.constraints import EnergyProfile
            if isinstance(energy_profile, EnergyProfile):
                total_min = cumulative_time / 60
                x_pts = np.linspace(0, cumulative_time, 200)
                y_pts = [energy_profile.target_energy_at(t / 60) for t in x_pts]
                fig.add_trace(go.Scatter(
                    x=x_pts.tolist(), y=y_pts,
                    mode="lines",
                    line=dict(color="#f39c12", width=2, dash="dash"),
                    name="Energy Target",
                ))
        except Exception:
            pass

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(text="Set Timeline", font=dict(size=14)),
        xaxis_title="Time (seconds)",
        yaxis_title="Level",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        annotations=annotations,
        height=350,
        dragmode="zoom",
    )

    return fig


def build_staircase_figure(
    set_tracks: list,
    energy_profile=None,
    show_transitions: bool = True,
    track_offsets: dict | None = None,
) -> go.Figure:
    """Build a staircase/waterfall timeline where each track sits on its own lane."""
    fig = go.Figure()

    sorted_tracks = sorted(set_tracks, key=lambda s: s.position)
    if not sorted_tracks:
        fig.update_layout(**DARK_LAYOUT, height=400)
        return fig

    lane_height = 0.6  # vertical spacing between lanes — tight for visible overlap
    annotations = []
    # Track colors for alternating visual distinction
    colors = ["#00d2ff", "#e94560", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#e67e22", "#3498db"]

    offsets = track_offsets or {}

    # Quantize to median BPM — scale each track's duration as if pitch-shifted
    bpms = [st.track.bpm for st in sorted_tracks if st.track.bpm]
    target_bpm = float(np.median(bpms)) if bpms else 120.0

    # Pre-compute start times with overlap, using quantized durations
    def _quantized_duration(st):
        raw = st.track.duration_sec or 300
        track_bpm = st.track.bpm or target_bpm
        return raw * (track_bpm / target_bpm)

    start_times = [0.0]
    for i in range(1, len(sorted_tracks)):
        prev_st = sorted_tracks[i - 1]
        prev_dur_q = _quantized_duration(prev_st)
        overlap_sec = (8 / target_bpm) * 60  # 8 beats at the common BPM
        start_times.append(start_times[-1] + prev_dur_q - overlap_sec)

    # Apply user offsets (keyed by position string)
    for i, st in enumerate(sorted_tracks):
        offset = offsets.get(str(st.position), 0)
        if offset:
            start_times[i] += offset

    for i, st in enumerate(sorted_tracks):
        track = st.track
        af = track.audio_features
        duration_q = _quantized_duration(st)
        color = colors[i % len(colors)]
        y_offset = -i * lane_height
        t_start = start_times[i]
        t_end = t_start + duration_q

        if af and af.waveform_overview:
            envelope = np.frombuffer(af.waveform_overview, dtype=np.float32)
            time_axis = np.linspace(t_start, t_end, len(envelope))
            # Scale envelope to fit within lane
            max_env = float(np.max(envelope)) if len(envelope) > 0 else 1.0
            scaled = (envelope / max_env * lane_height * 0.7) + y_offset if max_env > 0 else np.full_like(envelope, y_offset)

            fig.add_trace(go.Scattergl(
                x=time_axis, y=scaled,
                mode="lines", fill="tozeroy" if i == 0 else None,
                line=dict(color=color, width=1),
                name=f"{st.position}. {track.title or '?'}",
                hovertemplate=(
                    f"<b>{track.title}</b><br>"
                    f"Artist: {track.artist or '?'}<br>"
                    f"BPM: {f'{track.bpm:.0f}' if track.bpm else '?'} → {target_bpm:.0f} "
                    f"({((target_bpm / (track.bpm or target_bpm)) - 1) * 100:+.1f}%)"
                    f" | Key: {track.key or '?'}<br>"
                    "Time: %{x:.0f}s<extra></extra>"
                ),
            ))

            # Fill area for this lane
            baseline = np.full(len(envelope), y_offset)
            fig.add_trace(go.Scattergl(
                x=np.concatenate([time_axis, time_axis[::-1]]),
                y=np.concatenate([scaled, baseline[::-1]]),
                fill="toself",
                fillcolor=color.replace(")", ", 0.25)").replace("rgb", "rgba") if "rgb" in color else f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.25)",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            ))

        # Overlap zone between this track and the next
        if i < len(sorted_tracks) - 1 and show_transitions:
            next_start = start_times[i + 1]
            fig.add_vrect(
                x0=next_start, x1=t_end,
                fillcolor="rgba(243, 156, 18, 0.08)",
                line=dict(width=0),
                layer="below",
            )
            # Transition score annotation
            next_st = sorted_tracks[i + 1]
            if next_st.transition_score:
                annotations.append(dict(
                    x=(next_start + t_end) / 2,
                    y=y_offset - lane_height * 0.5,
                    text=f"<b>{next_st.transition_score:.2f}</b>",
                    showarrow=False,
                    font=dict(size=10, color="#f39c12"),
                ))

        # Track label on left margin
        annotations.append(dict(
            x=t_start,
            y=y_offset + lane_height * 0.55,
            text=f"<b>{st.position}.</b> {track.title or '?'}<br>"
                 f"<span style='font-size:10px'>{f'{track.bpm:.0f}' if track.bpm else '?'} BPM | {track.key or '?'}</span>",
            showarrow=False,
            font=dict(size=11, color="#e0e0e0"),
            xanchor="left",
        ))

        # Horizontal lane separator
        fig.add_hline(
            y=y_offset - lane_height * 0.5,
            line=dict(color="#2a2a4a", width=1, dash="dot"),
        )

    # Energy target curve overlay
    if energy_profile is not None:
        try:
            from djsetbuilder.setbuilder.constraints import EnergyProfile
            if isinstance(energy_profile, EnergyProfile):
                total_time = start_times[-1] + (sorted_tracks[-1].track.duration_sec or 300)
                x_pts = np.linspace(0, total_time, 200)
                # Scale energy curve to span the full lane range
                y_min = -(len(sorted_tracks) - 1) * lane_height - lane_height * 0.5
                y_pts = [
                    energy_profile.target_energy_at(t / 60) * abs(y_min)
                    for t in x_pts
                ]
                fig.add_trace(go.Scatter(
                    x=x_pts.tolist(), y=y_pts,
                    mode="lines",
                    line=dict(color="#f39c12", width=2, dash="dash"),
                    name="Energy Target",
                ))
        except Exception:
            pass

    total_lanes = len(sorted_tracks)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#16213e",
        plot_bgcolor="#0f3460",
        font=dict(color="#e0e0e0", size=11),
        margin=dict(l=40, r=20, t=30, b=40),
        title=dict(text=f"Set Timeline — Staircase ({target_bpm:.0f} BPM)", font=dict(size=14)),
        xaxis=dict(
            title="Time (seconds)",
            showgrid=False,
            zerolinecolor="#2a2a4a",
            rangeslider=dict(visible=True, thickness=0.05),
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.03),
        annotations=annotations,
        height=max(400, 60 * total_lanes + 120),
        dragmode="pan",
    )
    # Set yaxis separately — add_hline above injects yaxis props that conflict
    # with passing yaxis as a kwarg in the same update_layout call.
    fig.update_yaxes(
        visible=False,
        range=[-(total_lanes - 1) * lane_height - lane_height, lane_height],
        fixedrange=True,
    )

    return fig


def _add_band_traces(
    fig: go.Figure,
    time_axis: np.ndarray,
    bands: dict[str, np.ndarray],
    mask: np.ndarray,
    label: str,
    track,
    bpm: float,
    target_bpm: float,
) -> None:
    """Add stacked frequency band fills for a track in the transition view.

    Bands stack from bottom (low) to top (high) using cumulative y values.
    Used as fallback when subplots are not available.
    """
    cumulative = np.zeros(int(np.sum(mask)), dtype=np.float32)
    section = "outro" if label == "A" else "intro"

    for col_name, band_label, color in BAND_CONFIG:
        env = bands[col_name][mask]
        prev_y = cumulative.copy()
        cumulative = cumulative + env

        # Filled area between prev_y and cumulative
        fig.add_trace(go.Scattergl(
            x=np.concatenate([time_axis, time_axis[::-1]]),
            y=np.concatenate([cumulative, prev_y[::-1]]),
            fill="toself",
            fillcolor=_hex_to_rgba(color, 0.35),
            line=dict(width=0),
            name=f"{label}: {band_label}",
            hovertemplate=(
                f"<b>{track.title}</b> ({section})<br>"
                f"{band_label}<br>"
                f"BPM: {bpm:.0f} → {target_bpm:.0f}<br>"
                "Time: %{x:.1f}s<extra></extra>"
            ),
        ))

    # Top outline for visual crispness
    fig.add_trace(go.Scattergl(
        x=time_axis, y=cumulative,
        mode="lines",
        line=dict(color="rgba(255,255,255,0.3)", width=0.5),
        showlegend=False,
        hoverinfo="skip",
    ))


def _add_band_lane_trace(
    fig: go.Figure,
    time_axis: np.ndarray,
    env: np.ndarray,
    row: int,
    label: str,
    track,
    band_label: str,
    color: str,
    bpm: float,
    target_bpm: float,
) -> None:
    """Add a single band envelope trace to a specific subplot row."""
    from plotly.graph_objects import Scattergl

    section = "outro" if label == "A" else "intro"
    is_first_band_trace = label == "A"

    fig.add_trace(
        Scattergl(
            x=time_axis, y=env,
            mode="lines", fill="tozeroy",
            fillcolor=_hex_to_rgba(color, 0.25),
            line=dict(color=color, width=1),
            name=f"{label}: {track.title or '?'}",
            legendgroup=label,
            showlegend=(row == 1),
            hovertemplate=(
                f"<b>{track.title}</b> ({section})<br>"
                f"{band_label}<br>"
                f"Level: %{{y:.3f}}<br>"
                f"BPM: {bpm:.0f} → {target_bpm:.0f}<br>"
                "Time: %{x:.1f}s<extra></extra>"
            ),
        ),
        row=row, col=1,
    )


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert '#rrggbb' to 'rgba(r, g, b, alpha)'."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _compute_transition_timeline(
    af_a, af_b, track_a, track_b,
    overlap_seconds: float, b_offset: float, view_window: float,
):
    """Pre-compute mapped time axes and masks for both tracks.

    Returns (mapped_a, mask_a, show_from_raw_a, a_end_time,
             mapped_b, mask_b, show_until_raw_b, b_start_on_timeline,
             scale_a, scale_b, target_bpm) or None values when waveform data
    is missing.
    """
    bpm_a = track_a.bpm or 120
    bpm_b = track_b.bpm or 120
    target_bpm = (bpm_a + bpm_b) / 2
    scale_a = bpm_a / target_bpm
    scale_b = bpm_b / target_bpm

    waveform_a = _load_waveform(af_a, use_detail=True)
    mapped_a = mask_a = show_from_raw_a = None
    a_end_time = 0.0
    if waveform_a is not None:
        time_a, env_a = waveform_a
        duration_a_raw = float(time_a[-1]) if len(time_a) > 0 else 300
        show_from_raw_a = max(0, duration_a_raw - view_window / scale_a)
        mask_a = time_a >= show_from_raw_a
        mapped_a = (time_a[mask_a] - show_from_raw_a) * scale_a
        a_end_time = float(mapped_a[-1]) if len(mapped_a) > 0 else view_window

    b_start_on_timeline = a_end_time - overlap_seconds + b_offset

    waveform_b = _load_waveform(af_b, use_detail=True)
    mapped_b = mask_b = show_until_raw_b = None
    if waveform_b is not None:
        time_b, env_b = waveform_b
        show_until_raw_b = view_window / scale_b
        mask_b = time_b <= show_until_raw_b
        mapped_b = time_b[mask_b] * scale_b + b_start_on_timeline

    return (
        mapped_a, mask_a, show_from_raw_a, a_end_time,
        mapped_b, mask_b, show_until_raw_b, b_start_on_timeline,
        scale_a, scale_b, target_bpm,
    )


def build_transition_figure(
    track_a, af_a,
    track_b, af_b,
    overlap_seconds: float = 30.0,
    cues_a: list | None = None,
    cues_b: list | None = None,
    b_offset: float = 0.0,
) -> go.Figure:
    """Build a dual-waveform transition figure with both tracks on the same timeline.

    When frequency band data is available, renders 4 split lanes (High → Low,
    top to bottom) with both tracks overlaid per lane — each band normalized
    independently so you can read EQ crossover points.

    Falls back to single-waveform overlay when band data is missing.
    """
    bpm_a = track_a.bpm or 120
    bpm_b = track_b.bpm or 120
    view_window = overlap_seconds * 2

    bands_a = _load_band_envelopes(af_a, use_detail=True)
    bands_b = _load_band_envelopes(af_b, use_detail=True)
    use_bands = bands_a is not None and bands_b is not None

    tl = _compute_transition_timeline(
        af_a, af_b, track_a, track_b, overlap_seconds, b_offset, view_window,
    )
    (mapped_a, mask_a, show_from_raw_a, a_end_time,
     mapped_b, mask_b, show_until_raw_b, b_start_on_timeline,
     scale_a, scale_b, target_bpm) = tl

    if use_bands:
        return _build_transition_bands(
            track_a, af_a, track_b, af_b,
            bands_a, bands_b,
            mapped_a, mask_a, show_from_raw_a, a_end_time,
            mapped_b, mask_b, show_until_raw_b, b_start_on_timeline,
            scale_a, scale_b, target_bpm, bpm_a, bpm_b,
            overlap_seconds, cues_a, cues_b,
        )

    # --- Fallback: single-waveform overlay (original behavior) ---
    fig = go.Figure()

    waveform_a = _load_waveform(af_a, use_detail=True)
    if waveform_a is not None and mapped_a is not None:
        _time_a, env_a = waveform_a
        fig.add_trace(go.Scattergl(
            x=mapped_a, y=env_a[mask_a],
            mode="lines", fill="tozeroy",
            fillcolor="rgba(0, 210, 255, 0.25)",
            line=dict(color="#00d2ff", width=1),
            name=f"A: {track_a.title or '?'}",
            hovertemplate=(
                f"<b>{track_a.title}</b> (outro)<br>"
                f"BPM: {bpm_a:.0f} → {target_bpm:.0f}<br>"
                "Time: %{x:.1f}s<extra></extra>"
            ),
        ))
        if cues_a:
            max_a = float(np.max(env_a[mask_a])) if np.any(mask_a) else 1.0
            shifted_cues = [
                {**c, "start_sec": (c["start_sec"] - show_from_raw_a) * scale_a}
                for c in cues_a if c["start_sec"] >= show_from_raw_a
            ]
            add_cue_markers(fig, shifted_cues, max_a, prefix="A")

    waveform_b = _load_waveform(af_b, use_detail=True)
    if waveform_b is not None and mapped_b is not None:
        _time_b, env_b = waveform_b
        fig.add_trace(go.Scattergl(
            x=mapped_b, y=env_b[mask_b],
            mode="lines", fill="tozeroy",
            fillcolor="rgba(233, 69, 96, 0.2)",
            line=dict(color="#e94560", width=1),
            name=f"B: {track_b.title or '?'}",
            hovertemplate=(
                f"<b>{track_b.title}</b> (intro)<br>"
                f"BPM: {bpm_b:.0f} → {target_bpm:.0f}<br>"
                "Time: %{x:.1f}s<extra></extra>"
            ),
        ))
        if cues_b:
            max_b = float(np.max(env_b[mask_b])) if np.any(mask_b) else 1.0
            shifted_cues = [
                {**c, "start_sec": c["start_sec"] * scale_b + b_start_on_timeline}
                for c in cues_b if c["start_sec"] <= show_until_raw_b
            ]
            add_cue_markers(fig, shifted_cues, max_b, prefix="B")

    _add_transition_markers(fig, a_end_time, b_start_on_timeline, overlap_seconds)

    pitch_a = ((target_bpm / bpm_a) - 1) * 100
    pitch_b = ((target_bpm / bpm_b) - 1) * 100
    title = (
        f"Transition: {track_a.title or '?'} → {track_b.title or '?'} "
        f"@ {target_bpm:.0f} BPM (A: {pitch_a:+.1f}%, B: {pitch_b:+.1f}%)"
    )
    beat_sec = 60 / target_bpm
    bar_sec = beat_sec * 4
    dark = {k: v for k, v in DARK_LAYOUT.items() if k not in ("xaxis", "yaxis")}
    fig.update_layout(
        **dark,
        title=dict(text=title, font=dict(size=13)),
        xaxis=dict(
            title="Time (seconds)",
            gridcolor="rgba(83, 52, 131, 0.5)",
            gridwidth=1, dtick=bar_sec, tick0=0,
            minor=dict(dtick=beat_sec, gridcolor="rgba(83, 52, 131, 0.2)", gridwidth=1),
            zerolinecolor="#2a2a4a",
        ),
        yaxis=dict(gridcolor="#2a2a4a", zerolinecolor="#2a2a4a", title="Level"),
        showlegend=True, legend=dict(orientation="h", y=-0.15),
        height=350, dragmode="pan", uirevision="transition",
    )
    return fig


def _build_transition_bands(
    track_a, af_a, track_b, af_b,
    bands_a, bands_b,
    mapped_a, mask_a, show_from_raw_a, a_end_time,
    mapped_b, mask_b, show_until_raw_b, b_start_on_timeline,
    scale_a, scale_b, target_bpm, bpm_a, bpm_b,
    overlap_seconds, cues_a, cues_b,
) -> go.Figure:
    """Build a 4-row subplot transition figure with split frequency band lanes."""
    from plotly.subplots import make_subplots

    # Bands ordered top-to-bottom: High → Mid-high → Mid-low → Low
    band_order = list(reversed(BAND_CONFIG))

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_titles=[label for _, label, _ in band_order],
    )

    # Colors: A = blue tint, B = red tint
    color_a = "#00d2ff"
    color_b = "#e94560"

    for row_idx, (col_name, band_label, band_color) in enumerate(band_order, 1):
        # Collect both envelopes to compute shared normalization
        env_a_raw = bands_a[col_name][mask_a] if mapped_a is not None else np.array([])
        env_b_raw = bands_b[col_name][mask_b] if mapped_b is not None else np.array([])
        global_max = max(
            float(np.max(env_a_raw)) if len(env_a_raw) > 0 else 0,
            float(np.max(env_b_raw)) if len(env_b_raw) > 0 else 0,
            1e-6,
        )
        # Normalize so both tracks are on the same scale within this band
        env_a_norm = env_a_raw / global_max if len(env_a_raw) > 0 else env_a_raw
        env_b_norm = env_b_raw / global_max if len(env_b_raw) > 0 else env_b_raw

        if mapped_a is not None and len(env_a_norm) > 0:
            _add_band_lane_trace(
                fig, mapped_a, env_a_norm, row_idx,
                "A", track_a, band_label, color_a, bpm_a, target_bpm,
            )

        if mapped_b is not None and len(env_b_norm) > 0:
            _add_band_lane_trace(
                fig, mapped_b, env_b_norm, row_idx,
                "B", track_b, band_label, color_b, bpm_b, target_bpm,
            )

    # Overlap zone + markers on all subplots
    overlap_start = b_start_on_timeline
    overlap_end = a_end_time
    for row_idx in range(1, 5):
        if overlap_start < overlap_end:
            fig.add_vrect(
                x0=overlap_start, x1=overlap_end,
                fillcolor="rgba(243, 156, 18, 0.06)",
                line=dict(width=0),
                row=row_idx, col=1,
            )
        fig.add_vline(
            x=a_end_time, line=dict(color="#e94560", width=1, dash="dash"),
            row=row_idx, col=1,
        )
        fig.add_vline(
            x=b_start_on_timeline, line=dict(color="#00d2ff", width=1, dash="dash"),
            row=row_idx, col=1,
        )

    # Overlap annotation on top row only
    if overlap_start < overlap_end:
        fig.add_annotation(
            x=(overlap_start + overlap_end) / 2, y=1.0,
            text=f"Overlap ({overlap_end - overlap_start:.1f}s)",
            showarrow=False, font=dict(size=10, color="#f39c12"),
            xref="x", yref="y domain", row=1, col=1,
        )

    pitch_a = ((target_bpm / bpm_a) - 1) * 100
    pitch_b = ((target_bpm / bpm_b) - 1) * 100
    title = (
        f"Transition: {track_a.title or '?'} → {track_b.title or '?'} "
        f"@ {target_bpm:.0f} BPM (A: {pitch_a:+.1f}%, B: {pitch_b:+.1f}%)"
    )

    beat_sec = 60 / target_bpm
    bar_sec = beat_sec * 4

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#16213e",
        plot_bgcolor="#0f3460",
        font=dict(color="#e0e0e0", size=11),
        margin=dict(l=40, r=20, t=40, b=40),
        title=dict(text=title, font=dict(size=13)),
        showlegend=True,
        legend=dict(orientation="h", y=-0.05),
        height=600,
        dragmode="pan",
        uirevision="transition",
    )

    # Style the shared x-axis (bottom row) with beat grid
    fig.update_xaxes(
        gridcolor="rgba(83, 52, 131, 0.5)", gridwidth=1,
        dtick=bar_sec, tick0=0,
        minor=dict(dtick=beat_sec, gridcolor="rgba(83, 52, 131, 0.2)", gridwidth=1),
        zerolinecolor="#2a2a4a",
        row=4, col=1,
        title_text="Time (seconds)",
    )
    # Other rows: same grid, no title
    for row_idx in range(1, 4):
        fig.update_xaxes(
            gridcolor="rgba(83, 52, 131, 0.5)", gridwidth=1,
            dtick=bar_sec, tick0=0,
            minor=dict(dtick=beat_sec, gridcolor="rgba(83, 52, 131, 0.2)", gridwidth=1),
            zerolinecolor="#2a2a4a",
            row=row_idx, col=1,
        )

    # All y-axes: normalized 0-1, no labels
    for row_idx in range(1, 5):
        fig.update_yaxes(
            range=[0, 1.05], showticklabels=False,
            gridcolor="#2a2a4a", zerolinecolor="#2a2a4a",
            row=row_idx, col=1,
        )

    return fig


def _add_transition_markers(
    fig: go.Figure,
    a_end_time: float,
    b_start_on_timeline: float,
    overlap_seconds: float,
) -> None:
    """Add overlap zone, A-end and B-start markers to a single-pane transition figure."""
    overlap_start = b_start_on_timeline
    overlap_end = a_end_time
    if overlap_start < overlap_end:
        fig.add_vrect(
            x0=overlap_start, x1=overlap_end,
            fillcolor="rgba(243, 156, 18, 0.08)",
            line=dict(width=0),
            annotation_text=f"Overlap ({overlap_end - overlap_start:.1f}s)",
            annotation_font=dict(size=10, color="#f39c12"),
            annotation_position="top left",
        )
    fig.add_vline(
        x=a_end_time, line=dict(color="#e94560", width=1, dash="dash"),
        annotation_text="A ends", annotation_font=dict(size=9, color="#e94560"),
    )
    fig.add_vline(
        x=b_start_on_timeline, line=dict(color="#00d2ff", width=1, dash="dash"),
        annotation_text="B starts", annotation_font=dict(size=9, color="#00d2ff"),
    )


def add_cue_markers(
    fig: go.Figure,
    cue_points: list,
    max_level: float,
    prefix: str = "",
    below: bool = False,
) -> None:
    """Add cue point markers as vertical lines with labels on a figure."""
    for cue in cue_points:
        color = CUE_COLORS.get(cue.get("cue_type", "cue"), "#00d2ff")
        x_pos = cue["start_sec"]
        label = f"{prefix + ': ' if prefix else ''}{cue['name']}"

        fig.add_vline(
            x=x_pos,
            line=dict(color=color, width=2, dash="solid"),
            annotation_text=label,
            annotation_font=dict(size=9, color=color),
            annotation_position="top" if not below else "bottom",
        )

        # Loop region
        if cue.get("end_sec") and cue.get("cue_type") == "loop":
            fig.add_vrect(
                x0=x_pos, x1=cue["end_sec"],
                fillcolor=f"rgba({','.join(str(int(color.lstrip('#')[i:i+2], 16)) for i in (0, 2, 4))}, 0.15)",
                line=dict(width=0),
            )


# ── Taste DNA Figures ───────────────────────────────────────────────────


def build_camelot_radar(data: dict[int, dict[str, int]]) -> go.Figure:
    """Build a polar bar chart of Camelot key distribution.

    data: {1: {"A": 45, "B": 32}, ...} from camelot_distribution().
    """
    positions = list(range(1, 13))
    theta = [str(n) for n in positions]

    a_counts = [data.get(n, {}).get("A", 0) for n in positions]
    b_counts = [data.get(n, {}).get("B", 0) for n in positions]

    fig = go.Figure()
    fig.add_trace(go.Barpolar(
        r=a_counts,
        theta=theta,
        name="Minor (A)",
        marker_color="#00d2ff",
        opacity=0.8,
    ))
    fig.add_trace(go.Barpolar(
        r=b_counts,
        theta=theta,
        name="Major (B)",
        marker_color="#e94560",
        opacity=0.8,
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#16213e",
        plot_bgcolor="#0f3460",
        font=dict(color="#e0e0e0", size=11),
        title=dict(text="Camelot Key Distribution", font=dict(size=14)),
        polar=dict(
            bgcolor="#0f3460",
            radialaxis=dict(showticklabels=True, gridcolor="#2a2a4a"),
            angularaxis=dict(direction="clockwise", gridcolor="#2a2a4a"),
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.1),
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


def build_camelot_bar(data: dict[int, dict[str, int]]) -> go.Figure:
    """Build a grouped bar chart of Camelot key distribution.

    data: {1: {"A": 45, "B": 32}, ...} from camelot_distribution().
    """
    positions = list(range(1, 13))
    labels = [str(n) for n in positions]
    a_counts = [data.get(n, {}).get("A", 0) for n in positions]
    b_counts = [data.get(n, {}).get("B", 0) for n in positions]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=a_counts, name="Minor (A)",
        marker_color="#00d2ff", opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        x=labels, y=b_counts, name="Major (B)",
        marker_color="#e94560", opacity=0.85,
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        barmode="group",
        title=dict(text="Camelot Key Distribution", font=dict(size=14)),
        yaxis_title="Tracks",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
    )
    fig.update_xaxes(title="Camelot Position", dtick=1)
    return fig


def build_bpm_histogram(data: list[dict]) -> go.Figure:
    """Build a stacked BPM histogram colored by genre family.

    data: [{"bin_center": 124.0, "family": "Techno", "count": 12}, ...]
    """
    # Group by family
    families: dict[str, tuple[list[float], list[int]]] = {}
    for row in data:
        fam = row["family"]
        if fam not in families:
            families[fam] = ([], [])
        families[fam][0].append(row["bin_center"])
        families[fam][1].append(row["count"])

    fig = go.Figure()
    for family in sorted(families.keys()):
        centers, counts = families[family]
        color = FAMILY_COLORS.get(family, "#8892b0")
        fig.add_trace(go.Bar(
            x=centers,
            y=counts,
            name=family,
            marker_color=color,
            opacity=0.85,
        ))

    fig.update_layout(
        **DARK_LAYOUT,
        barmode="stack",
        title=dict(text="BPM Distribution by Genre Family", font=dict(size=14)),
        yaxis_title="Tracks",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
    )
    fig.update_xaxes(title="BPM", range=[88, 202], dtick=10)
    return fig


def build_energy_genre_heatmap(data: dict[str, dict[str, int]]) -> go.Figure:
    """Build a heatmap of energy levels x genre families.

    data: {"Techno": {"low": 5, "warmup": 12, ...}, ...}
    """
    from djsetbuilder.setbuilder.constraints import ENERGY_TAG_VALUES

    energy_levels = list(ENERGY_TAG_VALUES.keys())
    families = sorted(data.keys())

    z = []
    annotations = []
    for i, family in enumerate(families):
        row = []
        for j, level in enumerate(energy_levels):
            count = data.get(family, {}).get(level, 0)
            row.append(count)
            if count > 0:
                annotations.append(dict(
                    x=j, y=i, text=str(count),
                    showarrow=False,
                    font=dict(color="white" if count > 5 else "#8892b0", size=11),
                ))
        z.append(row)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=energy_levels,
        y=families,
        colorscale=[[0, "#0f3460"], [0.5, "#533483"], [1, "#e94560"]],
        showscale=True,
        colorbar=dict(title="Tracks"),
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#16213e",
        plot_bgcolor="#0f3460",
        font=dict(color="#e0e0e0", size=11),
        title=dict(text="Energy x Genre Family", font=dict(size=14)),
        xaxis_title="Energy Level",
        yaxis_title="Genre Family",
        annotations=annotations,
        margin=dict(l=80, r=20, t=50, b=60),
    )
    return fig


def build_mood_scatter(data: list[dict]) -> go.Figure:
    """Build a mood quadrant scatter plot.

    data: [{"title": ..., "x": happy-sad, "y": aggressive-relaxed,
            "energy": float, "genre_family": str}, ...]
    """
    # Group by family for separate traces
    by_family: dict[str, list[dict]] = {}
    for point in data:
        fam = point["genre_family"]
        by_family.setdefault(fam, []).append(point)

    fig = go.Figure()
    for family in sorted(by_family.keys()):
        points = by_family[family]
        color = FAMILY_COLORS.get(family, "#8892b0")
        fig.add_trace(go.Scatter(
            x=[p["x"] for p in points],
            y=[p["y"] for p in points],
            mode="markers",
            name=family,
            marker=dict(
                color=color,
                size=[max(4, p["energy"] * 14) for p in points],
                opacity=0.7,
                line=dict(width=0.5, color="#16213e"),
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "%{customdata[1]}<br>"
                "Happy-Sad: %{x:.2f}<br>"
                "Aggressive-Relaxed: %{y:.2f}<extra></extra>"
            ),
            customdata=[[p["title"], p["artist"]] for p in points],
        ))

    # Quadrant lines
    fig.add_hline(y=0, line=dict(color="#2a2a4a", width=1, dash="dash"))
    fig.add_vline(x=0, line=dict(color="#2a2a4a", width=1, dash="dash"))

    # Quadrant labels
    for text, x, y in [
        ("Happy + Aggressive", 0.5, 0.5),
        ("Happy + Relaxed", 0.5, -0.5),
        ("Sad + Aggressive", -0.5, 0.5),
        ("Sad + Relaxed", -0.5, -0.5),
    ]:
        fig.add_annotation(
            x=x, y=y, text=text, showarrow=False,
            font=dict(size=10, color="#4a4a6a"),
            xref="x", yref="y",
        )

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(text="Mood Quadrant (size = energy)", font=dict(size=14)),
        xaxis_title="Happy ← → Sad",
        yaxis_title="Relaxed ← → Aggressive",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
    )
    return fig
