"""Tests fuer das Intergalaktische Forschungsnetzwerk (IGFN) — pure Summier-Logik."""
from app.research.service import research_seconds, sum_top_labs


def test_no_network_uses_strongest_lab_only():
    # Stufe 0: nur das hoechste Labor zaehlt (top 1).
    assert sum_top_labs([10, 7, 3], 0) == 10


def test_network_level1_couples_two_best_labs():
    # Stufe 1: die zwei besten Labore summieren sich.
    assert sum_top_labs([10, 7, 3], 1) == 17


def test_network_level_caps_at_available_planets():
    # Mehr Netzwerkstufen als Planeten -> alle Labore zaehlen, kein Fehler.
    assert sum_top_labs([5, 4], 9) == 9


def test_empty_and_single_planet():
    assert sum_top_labs([], 3) == 0
    assert sum_top_labs([8], 0) == 8
    assert sum_top_labs([8], 5) == 8


def test_network_shortens_research_time():
    # Gekoppelte Labore (hoehere effektive Stufe) -> kuerzere Forschungszeit.
    cost = {"metal": 1000.0, "crystal": 1000.0, "deuterium": 0.0}
    solo = research_seconds(cost, sum_top_labs([10, 10], 0))   # nur 1 Labor (10)
    networked = research_seconds(cost, sum_top_labs([10, 10], 1))  # 2 Labore (20)
    assert networked < solo
