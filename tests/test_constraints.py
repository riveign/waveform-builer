"""Tests for energy profiles and constraints."""

from djsetbuilder.setbuilder.constraints import (
    dir_energy_to_numeric,
    parse_energy_string,
)


def test_parse_energy_string():
    profile = parse_energy_string("warmup:30:0.3,build:20:0.6,peak:40:0.9,cooldown:20:0.4")
    assert len(profile.segments) == 4
    assert profile.segments[0].name == "warmup"
    assert profile.segments[0].duration_min == 30
    assert profile.segments[0].target_energy == 0.3
    assert profile.total_duration_min == 110


def test_energy_interpolation():
    profile = parse_energy_string("warmup:30:0.3,peak:30:0.9")
    # At start of warmup
    assert profile.target_energy_at(0.0) == 0.3
    # At start of peak segment (should interpolate from warmup to peak)
    assert abs(profile.target_energy_at(30.0) - 0.3) < 0.01
    # Midway through peak
    energy = profile.target_energy_at(45.0)
    assert 0.3 < energy < 0.9


def test_dir_energy_tags():
    assert dir_energy_to_numeric("Low") == 0.2
    assert dir_energy_to_numeric("Peak") == 0.9
    assert dir_energy_to_numeric("Mid") == 0.5
    assert dir_energy_to_numeric(None) is None
