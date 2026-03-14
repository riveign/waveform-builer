"""Plotly figure builders for waveform visualization."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from djsetbuilder.analysis.waveform import envelope_to_time_axis

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
        **DARK_LAYOUT,
        height=80,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
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
                    f"BPM: {track.bpm:.0f if track.bpm else '?'} | Key: {track.key or '?'}<br>"
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
                 f"<span style='font-size:10px'>{track.bpm:.0f if track.bpm else '?'} BPM | {track.key or '?'}</span>",
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


def build_transition_figure(
    track_a, af_a,
    track_b, af_b,
    overlap_seconds: float = 30.0,
    cues_a: list | None = None,
    cues_b: list | None = None,
) -> go.Figure:
    """Build a dual-waveform transition comparison figure."""
    fig = go.Figure()

    # Track A outro
    waveform_a = _load_waveform(af_a, use_detail=True)
    if waveform_a is not None:
        time_a, env_a = waveform_a
        duration_a = float(time_a[-1]) if len(time_a) > 0 else 300
        # Show last overlap_seconds
        start_time = max(0, duration_a - overlap_seconds)
        mask = time_a >= start_time
        fig.add_trace(go.Scattergl(
            x=time_a[mask] - start_time,
            y=env_a[mask],
            mode="lines", fill="tozeroy",
            fillcolor="rgba(0, 210, 255, 0.3)",
            line=dict(color="#00d2ff", width=1),
            name=f"A: {track_a.title or '?'} (outro)",
        ))
        if cues_a:
            max_a = float(np.max(env_a[mask])) if np.any(mask) else 1.0
            shifted_cues = [
                {**c, "start_sec": c["start_sec"] - start_time}
                for c in cues_a if c["start_sec"] >= start_time
            ]
            add_cue_markers(fig, shifted_cues, max_a, prefix="A")

    # Track B intro
    waveform_b = _load_waveform(af_b, use_detail=True)
    if waveform_b is not None:
        time_b, env_b = waveform_b
        # Show first overlap_seconds
        mask = time_b <= overlap_seconds
        fig.add_trace(go.Scattergl(
            x=time_b[mask],
            y=-env_b[mask],  # Mirror below zero for visual separation
            mode="lines", fill="tozeroy",
            fillcolor="rgba(233, 69, 96, 0.3)",
            line=dict(color="#e94560", width=1),
            name=f"B: {track_b.title or '?'} (intro)",
        ))
        if cues_b:
            max_b = float(np.max(env_b[mask])) if np.any(mask) else 1.0
            intro_cues = [c for c in cues_b if c["start_sec"] <= overlap_seconds]
            add_cue_markers(fig, intro_cues, -max_b, prefix="B", below=True)

    # Transition zone marker
    fig.add_vrect(
        x0=overlap_seconds * 0.3, x1=overlap_seconds * 0.7,
        fillcolor="rgba(243, 156, 18, 0.1)",
        line=dict(width=0),
        annotation_text="Transition Zone",
        annotation_font=dict(size=10, color="#f39c12"),
    )

    title = f"Transition: {track_a.title or '?'} → {track_b.title or '?'}"
    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(text=title, font=dict(size=14)),
        xaxis_title="Time (seconds)",
        yaxis_title="Level",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        height=300,
    )

    return fig


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
