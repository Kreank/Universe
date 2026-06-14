"""Tests fuer die positions-gebundenen Exo-Minen (Antimaterie/Dunkle Materie).

Reine Wirtschafts-Formeln (DB-frei): Positions-Gate, Positions-Gradient (Pos voll / Nachbar halb),
Energiehunger drosselt die eigene Foerderung. Balance wird per Pfad-Suche geladen."""
from app.economy.service import (
    compute_rates,
    exotic_energy_use,
    exotic_production_raw,
)
from app.platform.balance import get_balance

_AC = "antimatter_collector"
_DC = "dark_matter_condenser"


def _cfg(name: str) -> dict:
    return get_balance().buildings[name]


def test_exotic_production_position_gate_and_gradient():
    c = _cfg(_AC)
    pb, pg = float(c["prod_base"]), float(c["prod_growth"])
    full = pb * 5 * (pg ** 5)  # Level 5, voller Positions-Mult (Pos 1 = 1.0)
    # Pos 1 (heiss, voll) -> Antimaterie in voller Hoehe.
    out1 = exotic_production_raw({_AC: 5}, 1)
    assert "antimatter" in out1
    assert abs(out1["antimatter"] - full) < 1e-6
    # Pos 2 (Nachbar) -> halber Ertrag.
    out2 = exotic_production_raw({_AC: 5}, 2)
    assert abs(out2["antimatter"] - full * 0.5) < 1e-6
    # Pos 3 (nicht erlaubt) -> kein Ertrag.
    assert exotic_production_raw({_AC: 5}, 3) == {}
    # Ohne Position -> nichts.
    assert exotic_production_raw({_AC: 5}, None) == {}
    # Level 0 -> nichts.
    assert exotic_production_raw({_AC: 0}, 1) == {}


def test_dark_matter_condenser_outer_positions():
    out15 = exotic_production_raw({_DC: 4}, 15)
    out14 = exotic_production_raw({_DC: 4}, 14)
    assert "dark_matter" in out15 and out15["dark_matter"] > 0
    assert abs(out14["dark_matter"] - out15["dark_matter"] * 0.5) < 1e-6
    # Innen (Pos 1) gibt es keine Dunkle Materie.
    assert exotic_production_raw({_DC: 4}, 1) == {}


def test_exotic_energy_use_only_on_allowed_position():
    c = _cfg(_AC)
    expect = float(c["energy_base"]) * 3 * (float(c["energy_growth"]) ** 3)
    assert abs(exotic_energy_use({_AC: 3}, 1) - expect) < 1e-6
    # Falsche Position -> kein Verbrauch (dort nicht baubar).
    assert exotic_energy_use({_AC: 3}, 7) == 0.0
    assert exotic_energy_use({_AC: 3}, None) == 0.0


def test_compute_rates_exposes_exotic_at_full_energy():
    bal = get_balance()
    speed = bal.speed
    c = _cfg(_AC)
    raw = float(c["prod_base"]) * 3 * (float(c["prod_growth"]) ** 3)
    # Viel Solar -> Energie deckt den Exo-Verbrauch -> factor 1.0.
    buildings = {_AC: 3, "solar_plant": 15}
    rates, energy, _caps = compute_rates(buildings, temp_max=220, energy_tech=0, position=1)
    assert abs(energy["factor"] - 1.0) < 1e-6
    assert "antimatter" in rates
    assert abs(rates["antimatter"] - round(raw * speed, 6)) < 1e-4
    # Exotisch taucht NICHT in den normalen Ressourcen-Caps auf.
    assert "antimatter" not in ("metal", "crystal", "deuterium")


def test_exotic_throttled_by_energy_deficit():
    # Exo-Mine mit zu schwachem Kraftwerk -> Teil-Defizit -> Foerderung gedrosselt (0 < factor < 1).
    buildings = {_AC: 5, "solar_plant": 5}
    rates, energy, _caps = compute_rates(buildings, temp_max=220, energy_tech=0, position=1)
    assert 0.0 < energy["factor"] < 1.0
    c = _cfg(_AC)
    raw = float(c["prod_base"]) * 5 * (float(c["prod_growth"]) ** 5)
    full = round(raw * get_balance().speed, 6)
    assert 0 < rates.get("antimatter", 0) < full


def test_compute_rates_no_exotic_on_wrong_position():
    buildings = {_AC: 5, "solar_plant": 15}
    rates, _energy, _caps = compute_rates(buildings, temp_max=80, energy_tech=0, position=7)
    assert "antimatter" not in rates
