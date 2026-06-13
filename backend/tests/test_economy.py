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


def test_fusion_reactor_burns_deuterium():
    """Fusionsreaktor erzeugt Energie UND verbrennt Deuterium (Doku 01 §4, Tech-Debt #3).
    Verbrauch ist fix (nicht energie-gedrosselt) und senkt die Netto-Deuterium-Rate."""
    bal = get_balance()
    speed = bal.speed
    fus = bal.buildings["fusion_reactor"]
    base_deut = float(bal.base_income.get("deuterium", 0))

    no_fusion = {"deuterium_synth": 5, "solar_plant": 10}
    with_fusion = {"deuterium_synth": 5, "solar_plant": 10, "fusion_reactor": 3}
    r0, e0, _ = compute_rates(no_fusion, temp_max=40, energy_tech=0)
    r1, e1, _ = compute_rates(with_fusion, temp_max=40, energy_tech=0)

    # Fusionsreaktor erhoeht die Energie-Erzeugung ...
    assert e1["produced"] > e0["produced"]
    # ... meldet einen Deuterium-Verbrauch ...
    burn = fus["deut_cost_base"] * 3 * (fus["deut_cost_growth"] ** 3)
    assert abs(e1["deuterium_burn"] - round(burn, 2)) < 0.05
    # ... und senkt die Netto-Deuterium-Rate genau um diesen Verbrauch (speed-skaliert).
    assert abs((r0["deuterium"] - r1["deuterium"]) - round(burn * speed, 4)) < 0.1


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


# ---- Befund #6: Deuterium-bewusste stueckweise Lazy-Akkumulation ----

def test_accrue_amount_linear_without_depletion():
    from app.economy.service import accrue_amount
    # Ohne Split: klassisches lineares Modell.
    assert accrue_amount(100.0, 50.0, 2.0) == 200.0
    # t_deplete >= dt_hours -> kein Split (Deut ueberlebt das Intervall).
    assert accrue_amount(100.0, 50.0, 2.0, t_deplete=5.0, rate_off=10.0) == 200.0


def test_accrue_amount_piecewise_throttles_after_depletion():
    from app.economy.service import accrue_amount
    # Metall/Kristall: bis t_deplete volle Rate (50), danach gedrosselte Off-Rate (20).
    grown = accrue_amount(100.0, 50.0, 10.0, t_deplete=4.0, rate_off=20.0)
    assert grown == 100.0 + 50.0 * 4.0 + 20.0 * 6.0  # 420
    # MUSS kleiner sein als das naive lineare Modell (das den Exploit belohnte).
    assert grown < accrue_amount(100.0, 50.0, 10.0)  # < 600


def test_accrue_amount_deuterium_resets_at_depletion():
    from app.economy.service import accrue_amount
    # Deut faellt bei t_deplete auf 0, waechst danach nur mit der Off-Rate (Fusion aus).
    grown = accrue_amount(1000.0, -100.0, 10.0, t_deplete=4.0, rate_off=20.0, is_deuterium=True)
    assert grown == 20.0 * 6.0  # 120, unabhaengig vom Startbestand


def test_accrue_amount_already_empty_tank_uses_off_rate_whole_interval():
    from app.economy.service import accrue_amount
    # Deut bereits leer (t_deplete=0) -> Metall laeuft das GANZE Intervall mit der Off-Rate.
    grown = accrue_amount(100.0, 50.0, 10.0, t_deplete=0.0, rate_off=20.0)
    assert grown == 100.0 + 20.0 * 10.0  # 300
