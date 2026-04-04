"""Teaching moments engine — explains why transitions work or struggle."""

from __future__ import annotations

from kiku.setbuilder.camelot import harmonic_score, parse_camelot
from kiku.setbuilder.scoring import genre_to_family


# ── Per-Transition Teaching ─────────────────────────────────────────────


def transition_teaching_moment(
    scores: dict,
    key_a: str | None,
    key_b: str | None,
    bpm_a: float | None,
    bpm_b: float | None,
    genre_a: str | None,
    genre_b: str | None,
) -> tuple[str, str | None]:
    """Generate a teaching moment and optional suggestion for a transition.

    Returns (teaching_moment, suggestion). suggestion is None for strong transitions.
    """
    total = scores.get("total", 0.0)
    suggestion: str | None = None

    # ── Strong transition (>= 0.8) — celebrate ──
    if total >= 0.8:
        return _explain_strength(scores, key_a, key_b, bpm_a, bpm_b), None

    # ── Good transition (0.6-0.8) — acknowledge ──
    if total >= 0.6:
        moment = _explain_good(scores, key_a, key_b, bpm_a, bpm_b, genre_a, genre_b)
        weakest = _weakest_dimension(scores)
        if weakest and scores.get(weakest, 1.0) < 0.5:
            suggestion = _suggest_improvement(weakest, scores, bpm_a, bpm_b, key_a, key_b)
        return moment, suggestion

    # ── Weak transition (< 0.6) — constructive ──
    moment = _explain_weakness(scores, key_a, key_b, bpm_a, bpm_b, genre_a, genre_b)
    weakest = _weakest_dimension(scores)
    if weakest:
        suggestion = _suggest_improvement(weakest, scores, bpm_a, bpm_b, key_a, key_b)
    return moment, suggestion


def _explain_strength(
    scores: dict, key_a: str | None, key_b: str | None,
    bpm_a: float | None, bpm_b: float | None,
) -> str:
    """Celebrate a strong transition."""
    h = scores.get("harmonic", 0)
    e = scores.get("energy_fit", 0)

    if h >= 0.85 and key_a and key_b:
        ca, cb = parse_camelot(key_a), parse_camelot(key_b)
        if ca and cb and ca == cb:
            base = f"Both tracks in {key_a} — perfect harmonic match."
        else:
            base = f"Clean key movement from {key_a} to {key_b}."
    elif e >= 0.8:
        base = "Energy flows naturally here."
    else:
        base = "Everything clicks on this transition."

    return base + " Your ear picked this."


def _explain_good(
    scores: dict, key_a: str | None, key_b: str | None,
    bpm_a: float | None, bpm_b: float | None,
    genre_a: str | None, genre_b: str | None,
) -> str:
    """Acknowledge a solid transition."""
    h = scores.get("harmonic", 0)
    b = scores.get("bpm_compat", 0)

    parts = []
    if h >= 0.8 and key_a and key_b:
        parts.append(f"The key shift from {key_a} to {key_b} keeps it moving.")
    elif b >= 0.8 and bpm_a and bpm_b:
        parts.append(f"Tempo stays locked at {bpm_a:.0f}\u2013{bpm_b:.0f} BPM.")
    else:
        parts.append("Solid transition \u2014 the pieces fit together.")

    if genre_a and genre_b and genre_to_family(genre_a) != genre_to_family(genre_b):
        parts.append("The genre shift adds character.")

    return " ".join(parts)


def _explain_weakness(
    scores: dict, key_a: str | None, key_b: str | None,
    bpm_a: float | None, bpm_b: float | None,
    genre_a: str | None, genre_b: str | None,
) -> str:
    """Constructive feedback for a weak transition."""
    weakest = _weakest_dimension(scores)

    if weakest == "harmonic" and key_a and key_b:
        return f"Key clash between {key_a} and {key_b} \u2014 this creates tension on the floor."
    if weakest == "bpm_compat" and bpm_a and bpm_b:
        diff_pct = abs(bpm_b - bpm_a) / bpm_a * 100 if bpm_a > 0 else 0
        return f"The BPM jump is {diff_pct:.0f}% \u2014 that's a noticeable shift."
    if weakest == "energy_fit":
        return "Big energy change here \u2014 the floor might feel the drop."
    if weakest == "genre_coherence":
        fa = genre_to_family(genre_a) if genre_a else "unknown"
        fb = genre_to_family(genre_b) if genre_b else "unknown"
        return f"Jumping from {fa} to {fb} \u2014 bold genre shift."

    return "This transition has some rough edges."


def _weakest_dimension(scores: dict) -> str | None:
    """Find the lowest-scoring dimension (excluding total and track_quality)."""
    dims = ["harmonic", "energy_fit", "bpm_compat", "genre_coherence"]
    valid = {d: scores[d] for d in dims if d in scores}
    if not valid:
        return None
    return min(valid, key=valid.get)  # type: ignore[arg-type]


def _suggest_improvement(
    weakest: str, scores: dict,
    bpm_a: float | None, bpm_b: float | None,
    key_a: str | None, key_b: str | None,
) -> str:
    """Suggest how to improve based on the weakest dimension."""
    if weakest == "harmonic":
        if key_a:
            ca = parse_camelot(key_a)
            if ca:
                adj_up = (ca[0] % 12) + 1
                adj_dn = ((ca[0] - 2) % 12) + 1
                return f"Try a track in {adj_up}{ca[1]} or {adj_dn}{ca[1]} for a smoother key transition."
        return "Look for a track with a compatible key."
    if weakest == "bpm_compat" and bpm_a and bpm_b:
        mid_bpm = (bpm_a + bpm_b) / 2
        return f"A bridge track around {mid_bpm:.0f} BPM could smooth this jump."
    if weakest == "energy_fit":
        return "Consider a track that bridges the energy gap gradually."
    if weakest == "genre_coherence":
        return "A cross-genre track could ease this transition."
    return "Consider rearranging tracks around this point."


# ── Set-Level Patterns ──────────────────────────────────────────────────


def detect_set_patterns(
    transitions: list[dict],
    energy_curve: list[float],
    key_journey: list[str | None],
    bpm_values: list[float | None],
) -> list[str]:
    """Detect set-level teaching patterns from aggregated data."""
    patterns: list[str] = []

    if not transitions:
        return patterns

    # Average scores per dimension
    avg: dict[str, float] = {}
    for dim in ["harmonic", "energy_fit", "bpm_compat", "genre_coherence"]:
        values = [t.get(dim, 0.5) for t in transitions]
        avg[dim] = sum(values) / len(values) if values else 0.5

    dim_labels = {
        "harmonic": "key relationships",
        "energy_fit": "energy flow",
        "bpm_compat": "tempo consistency",
        "genre_coherence": "genre cohesion",
    }

    # Strongest dimension
    best_dim = max(avg, key=avg.get)  # type: ignore[arg-type]
    if avg[best_dim] >= 0.7:
        patterns.append(
            f"Your strongest suit is {dim_labels[best_dim]} \u2014 "
            f"averaging {avg[best_dim]:.2f}. That's a signature element of your style."
        )

    # Energy arc shape
    if len(energy_curve) >= 3:
        mid = len(energy_curve) // 2
        start_avg = sum(energy_curve[:mid]) / mid if mid > 0 else 0
        end_avg = sum(energy_curve[mid:]) / (len(energy_curve) - mid)
        if end_avg > start_avg + 0.15:
            patterns.append("You build energy over the set \u2014 classic journey arc.")
        elif start_avg > end_avg + 0.15:
            patterns.append("You front-load energy and cool down \u2014 bold opening strategy.")
        elif max(energy_curve) - min(energy_curve) < 0.2:
            patterns.append("You keep energy steady \u2014 hypnotic, consistent vibe.")

    # Key adventure
    valid_keys = [k for k in key_journey if k]
    if len(valid_keys) >= 3:
        unique_keys = len(set(valid_keys))
        ratio = unique_keys / len(valid_keys)
        if ratio < 0.3:
            patterns.append("You stay close to home key \u2014 that's deep harmonic focus.")
        elif ratio > 0.7:
            patterns.append("You explore the Camelot wheel widely \u2014 adventurous harmonic ear.")

    # Weak spot
    weakest_dim = min(avg, key=avg.get)  # type: ignore[arg-type]
    if avg[weakest_dim] < 0.5:
        patterns.append(
            f"Your transitions could use work on {dim_labels[weakest_dim]} "
            f"(averaging {avg[weakest_dim]:.2f}). Focus here to level up."
        )

    return patterns
