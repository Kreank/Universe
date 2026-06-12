"""Tests fuer den koordinaten-geseedeten Feld-Roll (Planetengroesse / Glueck)."""
from app.planets.derive import _field_center, derive_planet, fields_max_for, rolled_fields
from app.platform.balance import get_balance


def _cfg():
    return get_balance().planets


def test_roll_is_stable_per_slot():
    # Gleicher Slot -> identischer Wert (seed nur an der Koordinate -> Backfill idempotent).
    a = rolled_fields(2, 137, 8)
    b = rolled_fields(2, 137, 8)
    assert a == b


def test_roll_varies_across_slots():
    # Nachbar-Slots derselben Position rollen unterschiedlich -> echte Variation.
    vals = {rolled_fields(1, s, 8) for s in range(1, 200)}
    assert len(vals) > 50  # weit gestreut, nicht konstant


def test_roll_within_variance_band_and_floor():
    cfg = _cfg()
    v = float(cfg["field_roll"]["variance"])
    floor = int(cfg["field_roll"]["floor"])
    for pos in range(1, len(cfg["field_curve"]) + 1):
        center = _field_center(pos)
        lo = max(floor, int(center * (1.0 - v)) - 1)
        hi = int(round(center * (1.0 + v))) + 1
        for s in range(1, 80):
            f = rolled_fields(3, s, pos)
            assert floor <= f
            assert lo <= f <= hi, (pos, s, f, lo, hi)


def test_mean_centered_on_curve():
    # Mittenlastige Verteilung -> Mittelwert ~ Zentrum (mode=center).
    center = _field_center(8)
    vals = [rolled_fields(4, s, 8) for s in range(1, 1001)]
    mean = sum(vals) / len(vals)
    assert abs(mean - center) < center * 0.03  # < 3% Abweichung


def test_max_field_planets_are_rare():
    # "Glueck": nur ein kleiner Anteil der Slots erreicht das obere Ende.
    center = _field_center(8)
    vals = [rolled_fields(5, s, 8) for s in range(1, 2001)]
    near_max = sum(1 for x in vals if x >= center * 1.25)
    assert near_max / len(vals) < 0.05  # < 5% sind Glueckstreffer


def test_homeworld_keeps_minimum_guarantee():
    cfg = _cfg()
    hw_min = int(cfg["homeworld_min_fields"])
    # Ein kalter Aussen-Slot (kleiner center) bleibt fuer Heimatplaneten >= Minimum ...
    assert fields_max_for(1, 1, 15, is_homeworld=True) >= hw_min
    # ... waehrend eine Kolonie dort darunter liegen darf.
    assert fields_max_for(1, 1, 15, is_homeworld=False) < hw_min


def test_derive_planet_keeps_type_and_temp_deterministic():
    # Typ/Temp bleiben rein positionsbestimmt (unabhaengig von galaxy/system).
    a = derive_planet(1, 5, 2)
    b = derive_planet(7, 199, 2)
    assert a["planet_type"] == b["planet_type"]
    assert a["temp_max"] == b["temp_max"]
    # Felder duerfen sich zwischen verschiedenen Slots unterscheiden.
    # (kein assert auf Gleichheit — Variation ist gewollt)


def test_variance_zero_is_deterministic(monkeypatch):
    # variance=0 -> exakt der Zentrum-Stuetzwert (alter Modus, kein Drift).
    import app.planets.derive as derive
    cfg = dict(_cfg())
    cfg["field_roll"] = {**cfg["field_roll"], "variance": 0.0}
    monkeypatch.setattr(derive, "_planets_cfg", lambda: cfg)
    assert rolled_fields(9, 9, 8) == _field_center(8)
