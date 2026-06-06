"""Smoke-Tests fuer die Wirtschafts-Formeln (Produktion, Energie, Lager, Lazy-Wachstum)."""
from app.economy.service import compute_rates
from app.platform.balance import get_balance


def test_storage_capacity_level0_is_starting_capacity():
    bal = get_balance()
    # 5000 * floor(2.5 * e^0) = 5000 * 2 = 10000 (Start-Lager).
    assert bal.storage_capacity(0) == 10000


def test_rates_with_starting_buildings_full_energy():
    buildings = {"metal_mine": 1, "crystal_mine": 1, "solar_plant": 1}
    rates, energy, caps = compute_rates(buildings, temp_max=40, energy_tech=0)
    speed = get_balance().speed
    # Verbrauch (11+11) = Produktion (22) -> factor 1.0.
    assert abs(energy["factor"] - 1.0) < 1e-6
    # Metall-Rate = (30*1*1.1^1 * factor + Grundeinkommen 30) * speed.
    expected = (30 * 1 * 1.1 * 1.0 + 30) * speed
    assert abs(rates["metal"] - round(expected, 4)) < 0.05
    assert caps["metal"] == 10000


def test_energy_deficit_throttles_mine_rate():
    # Hohe Mine ohne Kraftwerk -> Energiedefizit -> Drossel.
    buildings = {"metal_mine": 10}
    rates, energy, caps = compute_rates(buildings, temp_max=40, energy_tech=0)
    speed = get_balance().speed
    assert energy["factor"] < 1.0
    # Trotz Drossel laeuft das Grundeinkommen weiter.
    assert rates["metal"] >= 30 * speed - 0.01


def test_lazy_growth_is_capped_at_capacity():
    """Repliziert die Lazy-Formel: amount = min(capacity, amount + rate * dt)."""
    buildings = {"metal_mine": 1, "crystal_mine": 1, "solar_plant": 1}
    rates, _energy, caps = compute_rates(buildings, temp_max=40, energy_tech=0)
    amount = 9990.0
    dt_hours = 100.0  # sehr lange -> sollte deckeln
    grown = min(caps["metal"], amount + rates["metal"] * dt_hours)
    assert grown == caps["metal"]

    # Kurzes Intervall: linear ohne Deckel.
    grown_short = min(caps["metal"], 0.0 + rates["metal"] * 1.0)
    assert abs(grown_short - rates["metal"]) < 1e-6
