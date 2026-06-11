"""Reine Helfer der Stationierung/Eskorte (``app.fleet.stationing``)."""
from types import SimpleNamespace

from app.fleet.stationing import distribute_losses, escort_covers, escort_fee


def test_distribute_losses_greedy_fills_in_order():
    sources = [
        {"ships": {"fighter": 10, "cruiser": 2}},
        {"ships": {"fighter": 5}},
    ]
    # 8 fighter ueberleben gesamt -> erste Quelle bekommt 8, zweite 0; cruiser 1 -> erste.
    out = distribute_losses(sources, {"fighter": 8, "cruiser": 1})
    assert out[0] == {"fighter": 8, "cruiser": 1}
    assert out[1] == {}


def test_distribute_losses_overflow_to_second():
    sources = [{"ships": {"fighter": 4}}, {"ships": {"fighter": 6}}]
    out = distribute_losses(sources, {"fighter": 7})
    assert out[0] == {"fighter": 4}
    assert out[1] == {"fighter": 3}


def test_distribute_losses_none_survive():
    sources = [{"ships": {"fighter": 4}}]
    assert distribute_losses(sources, {}) == [{}]


def _station(galaxy, system, enabled=True, radius=5):
    return SimpleNamespace(galaxy=galaxy, system=system, escort_enabled=enabled, escort_radius=radius)


def test_escort_covers_within_radius():
    st = _station(1, 50, radius=5)
    # Route 40 -> 48 (gleiche Galaxie), Station bei 50 liegt in [40-5, 48+5]=[35,53].
    assert escort_covers(st, (1, 40, 48, 0)) is True


def test_escort_covers_out_of_range_or_galaxy():
    assert escort_covers(_station(1, 80, radius=2), (1, 40, 48, 0)) is False  # zu weit
    assert escort_covers(_station(2, 45, radius=5), (1, 40, 48, 0)) is False  # andere Galaxie
    assert escort_covers(_station(1, 45, enabled=False), (1, 40, 48, 0)) is False  # aus


def test_escort_fee():
    assert escort_fee(0.05, 100000) == 5000.0
    assert escort_fee(-1, 100000) == 0.0


def test_station_upkeep_sums_ship_fuel():
    """Treibstoff-Unterhalts-Basis = Summe(Schiff-fuel * Anzahl) — nur Bewegungs-relevante Schiffe."""
    from app.fleet.stationing import station_upkeep
    bal = SimpleNamespace(ships={"light_fighter": {"fuel": 20}, "battleship": {"fuel": 500}})
    assert station_upkeep({"light_fighter": 3, "battleship": 2}, bal) == 3 * 20 + 2 * 500
    assert station_upkeep({}, bal) == 0.0
    assert station_upkeep({"unknown_ship": 5}, bal) == 0.0   # unbekannt -> 0
