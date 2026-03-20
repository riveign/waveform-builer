"""Configuration endpoints — energy presets, genre families, and scoring weights."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from kiku.api.schemas import (
    EnergyPresetResponse,
    EnergySegmentResponse,
    GenreFamilyResponse,
    ScoringWeightsRequest,
    ScoringWeightsResponse,
)
from kiku.setbuilder.constraints import get_energy_presets, parse_energy_string
from kiku.setbuilder.scoring import COMPATIBLE_FAMILIES, GENRE_FAMILIES

router = APIRouter(prefix="/api/config", tags=["config"])

# Human-readable descriptions for built-in presets (Kiku voice)
_PRESET_DESCRIPTIONS: dict[str, str] = {
    "warmup": "Ease into the night. Low energy building gradually — perfect for opening sets.",
    "peak-time": "Straight to the top. High energy throughout for peak hour domination.",
    "journey": "The full arc. Build up, peak, wind down — a complete story in one set.",
    "afterhours": "Late night vibes. Steady mid-energy with a gentle descent.",
}


@router.get("/energy-presets", response_model=list[EnergyPresetResponse])
def list_energy_presets():
    """Return available energy presets with their segments and descriptions."""
    presets = get_energy_presets()
    result: list[EnergyPresetResponse] = []

    for name, raw_string in presets.items():
        profile = parse_energy_string(raw_string)
        total_min = profile.total_duration_min
        segments = [
            EnergySegmentResponse(
                name=seg.name,
                target_energy=seg.target_energy,
                duration_pct=round(seg.duration_min / total_min, 3) if total_min > 0 else 0.0,
            )
            for seg in profile.segments
        ]
        result.append(EnergyPresetResponse(
            name=name,
            description=_PRESET_DESCRIPTIONS.get(name, ""),
            segments=segments,
        ))

    return result


@router.get("/genre-families", response_model=list[GenreFamilyResponse])
def list_genre_families():
    """Return genre families with their member genres and compatibility info."""
    result: list[GenreFamilyResponse] = []

    for family_name, genres in GENRE_FAMILIES.items():
        compatible = [
            other
            for pair in COMPATIBLE_FAMILIES
            if family_name in pair
            for other in pair
            if other != family_name
        ]
        result.append(GenreFamilyResponse(
            family_name=family_name,
            genres=genres,
            compatible_with=sorted(compatible),
        ))

    return result


@router.get("/scoring-weights", response_model=ScoringWeightsResponse)
def get_scoring_weights():
    """Return current scoring weights — the balance behind every transition score."""
    from kiku.config import SCORING_WEIGHTS

    return ScoringWeightsResponse(**SCORING_WEIGHTS)


@router.put("/scoring-weights", response_model=ScoringWeightsResponse)
def update_scoring_weights(body: ScoringWeightsRequest):
    """Update global scoring weights. Weights must sum to ~1.0 (within 0.01)."""
    from kiku.config import save_scoring_weights

    weights = body.model_dump()
    try:
        updated = save_scoring_weights(weights)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ScoringWeightsResponse(**updated)
