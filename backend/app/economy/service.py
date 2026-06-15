"""Wirtschafts-Logik: Produktions-/Energie-Formeln und Lazy-Ressourcen (ADR-002).

Alle Zahlen stammen aus balance.json (NICHTS hartkodiert). Energie ist eine Bilanz
(Produktion - Verbrauch); ein Defizit drosselt die Minen-Rate ueber ``factor``."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import Building, Planet, Research, Resource, Ship

RESOURCE_KEYS = ("metal", "crystal", "deuterium")
# Exotische, KONTOWEITE Ressourcen (auf dem Player, kein Lager/Cap). Pro Planet wird je Exo-Mine
# eine Resource-Zeile als Lazy-Akkumulator gefuehrt und bei jedem Refresh aufs Konto ausgekehrt.
EXOTIC_KEYS = ("antimatter", "dark_matter")
STORAGE_BUILDING = {
    "metal": "metal_storage",
    "crystal": "crystal_storage",
    "deuterium": "deuterium_tank",
}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


async def get_building_levels(session: AsyncSession, planet_id: uuid.UUID) -> dict[str, int]:
    """Map type->level aller Gebaeude eines Planeten."""
    rows = (await session.execute(
        select(Building).where(Building.planet_id == planet_id)
    )).scalars().all()
    return {b.type: b.level for b in rows}


async def get_research_levels(session: AsyncSession, player_id: uuid.UUID) -> dict[str, int]:
    """Map type->level aller Forschungen eines Spielers."""
    rows = (await session.execute(
        select(Research).where(Research.player_id == player_id)
    )).scalars().all()
    return {r.type: r.level for r in rows}


def solar_satellite_energy(temp_max: int, count: int) -> float:
    """Energie stationierter Solarsatelliten (OGame): je Sat floor((temp_max + offset) / divisor),
    temperaturabhaengig -> sonnennahe (heisse) Planeten produzieren mehr. Nie negativ."""
    if count <= 0:
        return 0.0
    cfg = get_balance().ships.get("solar_satellite", {}).get("energy_prod")
    if not cfg:
        return 0.0
    per_sat = max(0, int((temp_max + int(cfg.get("temp_offset", 0))) // int(cfg.get("divisor", 1))))
    return float(per_sat * int(count))


def exotic_production_raw(buildings: dict[str, int], position: int | None) -> dict[str, float]:
    """Roh-Produktion exotischer Materie (pro Stunde, speed=1, VOR Energie-Drossel) der Exo-Minen
    auf diesem Planeten. Reine Funktion -> testbar. Positions-gebunden: nur baubar/ertragreich auf
    den ``allowed_positions`` des Gebaeudes, der Ertrag wird mit ``position_yield`` (Pos-Gradient)
    multipliziert. Liefert {exotic_prod-Ressource: rate}, z.B. {"antimatter": 12.3}."""
    if position is None:
        return {}
    b = get_balance().buildings
    out: dict[str, float] = {}
    for name, cfg in b.items():
        if not isinstance(cfg, dict) or "exotic_prod" not in cfg:
            continue
        level = int(buildings.get(name, 0))
        if level <= 0:
            continue
        if int(position) not in [int(p) for p in cfg.get("allowed_positions", [])]:
            continue
        pmult = float(cfg.get("position_yield", {}).get(str(int(position)), 0.0))
        if pmult <= 0:
            continue
        raw = float(cfg["prod_base"]) * level * (float(cfg["prod_growth"]) ** level) * pmult
        res = cfg["exotic_prod"]
        out[res] = out.get(res, 0.0) + raw
    return out


def exotic_energy_use(buildings: dict[str, int], position: int | None) -> float:
    """Energieverbrauch der Exo-Minen (zaehlt in die Energiebilanz -> drosselt bei Defizit ALLE
    Produktion). Nur Minen auf einer erlaubten Position zaehlen (anderswo nicht baubar)."""
    if position is None:
        return 0.0
    b = get_balance().buildings
    total = 0.0
    for name, cfg in b.items():
        if not isinstance(cfg, dict) or "exotic_prod" not in cfg:
            continue
        level = int(buildings.get(name, 0))
        if level <= 0 or int(position) not in [int(p) for p in cfg.get("allowed_positions", [])]:
            continue
        total += float(cfg["energy_base"]) * level * (float(cfg["energy_growth"]) ** level)
    return total


def compute_production_and_energy(
    buildings: dict[str, int],
    temp_max: int,
    energy_tech: int,
    mining_level: int = 0,
    solar_satellites: int = 0,
    extraction_level: int = 0,
    extraction_mastery_level: int = 0,
    megastructure_mining_mult: float = 1.0,
    position: int | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Berechnet (Minen-Roh-Produktion pro Stunde bei speed=1) und die Energie-Bilanz.

    Rueckgabe:
      rates_raw: {metal, crystal, deuterium [, antimatter/dark_matter]} = Produktion OHNE
                 Grundeinkommen, OHNE Drossel, OHNE Speed (das addiert/skaliert der Aufrufer).
                 Exotische Schluessel (nur bei ``position`` mit Exo-Mine) sind kontoweit, NICHT
                 in RESOURCE_KEYS -> der Cap-/Speicher-Loop ignoriert sie.
      energy:    {produced, consumed, balance, factor}
    """
    bal = get_balance()
    b = bal.buildings

    def lvl(name: str) -> int:
        return int(buildings.get(name, 0))

    def prod(name: str) -> float:
        cfg = b[name]
        level = lvl(name)
        if level <= 0:
            return 0.0
        return cfg["prod_base"] * level * (cfg["prod_growth"] ** level)

    def energy_use(name: str) -> float:
        cfg = b[name]
        level = lvl(name)
        if level <= 0:
            return 0.0
        return cfg["energy_base"] * level * (cfg["energy_growth"] ** level)

    # Minen-Foerderung (Forschung): Bergbau-Effizienz + Foerdertechnik + wiederholbare
    # Foerder-Meisterschaft, alle additiv je Stufe.
    eff = bal.data["research"].get("effects", {})
    mining_mult = (
        1.0
        + float(eff.get("mining_per_level", 0)) * int(mining_level)
        + float(eff.get("extraction_per_level", 0)) * int(extraction_level)
        + float(eff.get("extraction_mastery_per_level", 0)) * int(extraction_mastery_level)
    )
    # Megastruktur Materie-Dekompressor: imperiumsweiter multiplikativer Foerder-Bonus.
    mining_mult *= float(megastructure_mining_mult)

    # -- Roh-Produktion der Minen (pro Stunde, speed=1) ----------------------
    metal_raw = prod("metal_mine") * mining_mult
    crystal_raw = prod("crystal_mine") * mining_mult
    # Deuterium-Synthese: temperaturabhaengiger Faktor (heiss = weniger)
    deut_temp_factor = 1.36 - 0.004 * temp_max
    deut_raw = prod("deuterium_synth") * deut_temp_factor * mining_mult

    # -- Energie: Verbrauch der Minen ----------------------------------------
    consumed = energy_use("metal_mine") + energy_use("crystal_mine") + energy_use("deuterium_synth")
    # Exo-Minen sind energiehungrig: ihr Verbrauch zaehlt mit -> ein Defizit drosselt (factor)
    # auch ihre eigene Foerderung. Das ist die gewollte natuerliche Bremse (Energie statt Cap).
    consumed += exotic_energy_use(buildings, position)

    # -- Energie: Erzeugung (Solarkraftwerk + Solarsatelliten + Fusion) ------
    solar = b["solar_plant"]
    solar_lvl = lvl("solar_plant")
    produced = 0.0
    if solar_lvl > 0:
        produced += solar["energy_prod_base"] * solar_lvl * (solar["energy_prod_growth"] ** solar_lvl)
    # Solarsatelliten (Schiffe, auf dem Planeten stationiert): temperaturabhaengig.
    produced += solar_satellite_energy(temp_max, solar_satellites)
    fusion_lvl = lvl("fusion_reactor")
    fusion_deut_use = 0.0
    if fusion_lvl > 0:
        fus = b["fusion_reactor"]
        # Doku 01 §4: 30 * lvl * (1.05 + 0.01*EnergieTech)^lvl
        produced += fus["energy_prod_base"] * fusion_lvl * ((1.05 + 0.01 * energy_tech) ** fusion_lvl)
        # Fusionsreaktor verbrennt Deuterium (Doku 01 §4): deut_cost_base * lvl * growth^lvl pro Stunde.
        fusion_deut_use = fus.get("deut_cost_base", 0) * fusion_lvl * (fus.get("deut_cost_growth", 1.0) ** fusion_lvl)

    factor = 1.0 if consumed <= 0 else min(1.0, produced / consumed)

    rates_raw = {"metal": metal_raw, "crystal": crystal_raw, "deuterium": deut_raw}
    # Exotische Roh-Produktion (kontoweit, positions-gebunden) als Zusatz-Keys anhaengen.
    rates_raw.update(exotic_production_raw(buildings, position))
    energy = {
        "produced": round(produced, 2),
        "consumed": round(consumed, 2),
        "balance": round(produced - consumed, 2),
        "factor": round(factor, 4),
        "deuterium_burn": round(fusion_deut_use, 2),
    }
    return rates_raw, energy


def compute_rates(
    buildings: dict[str, int],
    temp_max: int,
    energy_tech: int,
    mining_level: int = 0,
    storage_level: int = 0,
    solar_satellites: int = 0,
    production_mult: float = 1.0,
    extraction_level: int = 0,
    extraction_mastery_level: int = 0,
    megastructure_mining_mult: float = 1.0,
    position: int | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Liefert (effektive Stundenraten inkl. Grundeinkommen & Speed, energy, capacities).

    ``production_mult`` (z. B. Gouverneur-Bonus) wirkt NUR auf den Minen-/Gebaeudeanteil,
    NICHT auf das freie Grundeinkommen und NICHT auf den fixen Deut-Verbrauch des Fusions-
    reaktors (Befund D-1: sonst wuerde der Bonus den Trickle mitskalieren und beim Deut
    faelschlich (Produktion-Verbrauch)*mult statt Produktion*mult-Verbrauch rechnen)."""
    bal = get_balance()
    speed = bal.speed
    rates_raw, energy = compute_production_and_energy(
        buildings, temp_max, energy_tech, mining_level, solar_satellites,
        extraction_level, extraction_mastery_level, megastructure_mining_mult, position,
    )
    factor = energy["factor"]
    base = bal.base_income

    rates: dict[str, float] = {}
    for key in RESOURCE_KEYS:
        # Minen werden gedrosselt + produktions-skaliert, Grundeinkommen nicht; alles mit Speed.
        effective = rates_raw[key] * factor * production_mult + float(base.get(key, 0))
        # Fusionsreaktor verbrennt Deuterium (fixer Verbrauch, NICHT energie-/bonus-skaliert).
        if key == "deuterium":
            effective -= energy.get("deuterium_burn", 0.0)
        rates[key] = round(effective * speed, 4)

    # Exotische Materie (kontoweit): effektive Rate = Roh * Energie-factor * Speed. KEIN
    # production_mult (Gouverneur/Dekompressor wirken nur auf Minen), KEIN Grundeinkommen, KEIN Cap.
    for key, raw in rates_raw.items():
        if key not in RESOURCE_KEYS:
            rates[key] = round(raw * factor * speed, 6)

    # Speichertechnik (Forschung): +X% Lagerkapazitaet je Stufe.
    store_mult = 1.0 + float(bal.data["research"].get("effects", {}).get("storage_per_level", 0)) * int(storage_level)
    capacities = {
        key: bal.storage_capacity(int(buildings.get(STORAGE_BUILDING[key], 0))) * store_mult
        for key in RESOURCE_KEYS
    }
    return rates, energy, capacities


def accrue_amount(
    amount: float,
    rate_on: float,
    dt_hours: float,
    *,
    t_deplete: float | None = None,
    rate_off: float | None = None,
    is_deuterium: bool = False,
) -> float:
    """Reine Lazy-Akkumulation einer Ressource ueber ``dt_hours`` (VOR Cap/Floor).

    Ohne ``(t_deplete, rate_off)`` das klassische lineare ADR-002-Modell:
    ``amount + rate_on * dt_hours``.

    Mit gesetztem ``t_deplete`` (Deut-Erschoepfungszeit) UND ``rate_off`` (Fusion-AUS-Rate)
    und ``t_deplete < dt_hours`` -> stueckweise Integration (Befund #6): bis ``t_deplete``
    die volle ``rate_on``, danach die gedrosselte ``rate_off``. Deuterium faellt bei
    ``t_deplete`` per Definition auf 0 und waechst danach nur noch mit ``rate_off`` (>=0)."""
    if t_deplete is not None and rate_off is not None and t_deplete < dt_hours:
        t_on = max(0.0, t_deplete)
        t_off = dt_hours - t_on
        if is_deuterium:
            return rate_off * t_off
        return amount + rate_on * t_on + rate_off * t_off
    return amount + rate_on * dt_hours


async def refresh_resources(session: AsyncSession, planet: Planet) -> dict:
    """Lazy-Update (ADR-002): wendet die ALTE Rate ueber die verstrichene Zeit an,
    deckelt auf die Kapazitaet, berechnet dann die NEUE Rate und persistiert beides.

    Liefert das Ressourcen-Objekt im API-Format (inkl. Energie-Bilanz)."""
    now = _now()
    buildings = await get_building_levels(session, planet.id)
    research = await get_research_levels(session, planet.player_id)
    energy_tech = research.get("energy_tech", 0)
    # Megastruktur Materie-Dekompressor: imperiumsweiter Foerder-Bonus.
    from app.megastructure.service import effect_mult
    mega_mining_mult = await effect_mult(session, planet.player_id, "mining_speed")
    # Auf dem Planeten stationierte Solarsatelliten (fleet_id NULL) -> Energiebeitrag.
    solar_sats = int((await session.execute(
        select(Ship.count).where(
            Ship.planet_id == planet.id,
            Ship.fleet_id.is_(None),
            Ship.type == "solar_satellite",
        )
    )).scalar() or 0)
    # Gouverneur-Bonus (Kommandeur auf dem Planeten) -> wirkt als production_mult NUR auf den
    # Minen-/Gebaeudeanteil (Befund D-1), daher vor compute_rates ermitteln.
    gov_mult = 1.0
    if getattr(planet, "governor_commander_id", None):
        from app.commander.service import governor_production_mult
        from app.platform.models import Commander as _Commander
        gov = await session.get(_Commander, planet.governor_commander_id)
        gov_mult = governor_production_mult(gov, get_balance())

    new_rates, energy, capacities = compute_rates(
        buildings, planet.temp_max, energy_tech,
        research.get("mining_efficiency", 0), research.get("storage_tech", 0),
        solar_sats, production_mult=gov_mult,
        extraction_level=research.get("extraction_tech", 0),
        extraction_mastery_level=research.get("extraction_mastery", 0),
        megastructure_mining_mult=mega_mining_mult,
        position=planet.position,
    )

    rows = (await session.execute(
        select(Resource).where(
            Resource.planet_id == planet.id,
            Resource.type.in_(RESOURCE_KEYS),
        )
    )).scalars().all()
    by_type = {r.type: r for r in rows}

    # --- Befund #6: Deuterium-bewusste stueckweise Integration (ADR-002-Verfeinerung) -------
    # Ein fusion-abhaengiger Planet kann mehr Deut verbrennen, als er synthetisiert -> die
    # Deut-"Rate of record" ist negativ. Geht der Spieler offline, bis das Deut leer ist,
    # schaltet der Fusionsreaktor real ab -> Energie sinkt -> Minen drosseln. Das rein lineare
    # Lazy-Modell wuerde Metall/Kristall die ganze Zeit mit der vollen (fusion-gestuetzten) Rate
    # gutschreiben und so nie produziertes Material verschenken (Exploit: Deut-Tank leerlaufen
    # lassen). Daher: laeuft das Deut im Intervall aus, splitten wir am Erschoepfungszeitpunkt
    # und rechnen den Rest mit dem Fusion-AUS-Regime (gleiche Pipeline, fusion_reactor=0 ->
    # keine Fusionsenergie UND kein Deut-Burn).
    deut_row = by_type.get("deuterium")
    deut_start = deut_row.amount if deut_row is not None else 0.0
    deut_rate_rec = deut_row.rate if deut_row is not None else 0.0  # bisherige (Fusion-AN-)Rate
    off_rates: dict[str, float] | None = None
    t_deplete = 0.0
    if deut_rate_rec < 0:
        # Stunden bis das Deut bei der bisherigen Rate auf 0 faellt (>=0).
        t_deplete = deut_start / (-deut_rate_rec)
        buildings_off = {**buildings, "fusion_reactor": 0}
        off_rates, _e_off, _c_off = compute_rates(
            buildings_off, planet.temp_max, energy_tech,
            research.get("mining_efficiency", 0), research.get("storage_tech", 0), solar_sats,
            production_mult=gov_mult,
            extraction_level=research.get("extraction_tech", 0),
            extraction_mastery_level=research.get("extraction_mastery", 0),
            megastructure_mining_mult=mega_mining_mult,
            position=planet.position,
        )

    result: dict[str, dict] = {}
    for key in RESOURCE_KEYS:
        row = by_type.get(key)
        cap = capacities[key]
        if row is None:
            # Sollte nach Registrierung existieren; defensiv anlegen.
            row = Resource(planet_id=planet.id, type=key, amount=0.0, rate=0.0, last_updated=now)
            session.add(row)
            by_type[key] = row

        last = row.last_updated or now
        if last.tzinfo is None:
            last = last.replace(tzinfo=dt.timezone.utc)
        dt_hours = max(0.0, (now - last).total_seconds() / 3600.0)
        # ALTE Rate ueber das Intervall anwenden (deut-bewusst stueckweise, Befund #6),
        # dann deckeln. OGame-Modell: die Produktion (Minen) stoppt am Lager-Cap, ABER bereits
        # vorhandener Ueberschuss (extern zugefuehrt: Beute/Abbau/Recycling/Transport) bleibt
        # erhalten -> nur das Wachstum DURCH PRODUKTION wird auf max(cap, Startbestand) gedeckelt.
        start_amt = row.amount
        grown = accrue_amount(
            start_amt, row.rate, dt_hours,
            t_deplete=(t_deplete if off_rates is not None else None),
            rate_off=(off_rates[key] if off_rates is not None else None),
            is_deuterium=(key == "deuterium"),
        )
        row.amount = max(0.0, min(grown, max(cap, start_amt)))
        # NEUE Rate setzen und Zeitstempel aktualisieren.
        row.rate = new_rates[key]
        row.last_updated = now

        result[key] = {
            "amount": round(row.amount, 2),
            "rate": round(row.rate, 2),
            "capacity": round(cap, 2),
        }

    # --- Exotische Materie (PRO PLANET, wie metal/crystal — KEIN Sweep aufs Konto mehr) ----------
    # Lazy-Akkumulator je Planet (amount + rate + last_updated), UNCAPPED (kein Lagergebaeude).
    # Bewusste Design-Entscheidung 2026-06-15: Exoten bleiben am Produktions-Planeten, muessen
    # transportiert werden und sind erbeutbar (Spannung) — nicht mehr kontoweit-global.
    exotic_rows = (await session.execute(
        select(Resource).where(
            Resource.planet_id == planet.id,
            Resource.type.in_(EXOTIC_KEYS),
        )
    )).scalars().all()
    exotic_by_type = {r.type: r for r in exotic_rows}
    exotic_out: dict[str, dict] = {}
    for key in EXOTIC_KEYS:
        new_rate = float(new_rates.get(key, 0.0))
        row = exotic_by_type.get(key)
        if row is None:
            if new_rate <= 0:
                continue  # nie produziert -> keine Zeile noetig
            session.add(Resource(planet_id=planet.id, type=key, amount=0.0, rate=new_rate, last_updated=now))
            exotic_out[key] = {"amount": 0.0, "rate": round(new_rate, 4)}
            continue
        last = row.last_updated or now
        if last.tzinfo is None:
            last = last.replace(tzinfo=dt.timezone.utc)
        dt_hours = max(0.0, (now - last).total_seconds() / 3600.0)
        row.amount = max(0.0, float(row.amount or 0.0) + float(row.rate or 0.0) * dt_hours)
        row.rate = new_rate
        row.last_updated = now
        exotic_out[key] = {"amount": round(row.amount, 2), "rate": round(new_rate, 4)}
    if exotic_out:
        result["exotic"] = exotic_out

    result["energy"] = energy
    return result


async def spend_resources(session: AsyncSession, planet: Planet, cost: dict[str, float]) -> bool:
    """Versucht, ``cost`` abzuziehen (metal/crystal/deuterium UND Exoten antimatter/dark_matter).
    Aktualisiert zuerst lazy. Gibt False zurueck, wenn nicht leistbar (dann wird NICHTS abgezogen).
    Exoten sind pro Planet (kein Konto mehr); fehlende Exoten-Zeile = 0."""
    await refresh_resources(session, planet)
    keys = RESOURCE_KEYS + EXOTIC_KEYS
    rows = (await session.execute(
        select(Resource).where(
            Resource.planet_id == planet.id,
            Resource.type.in_(keys),
        )
    )).scalars().all()
    by_type = {r.type: r for r in rows}
    for key in keys:
        need = float(cost.get(key, 0))
        have = by_type[key].amount if key in by_type else 0.0
        if have + 1e-6 < need:
            return False
    for key in keys:
        need = float(cost.get(key, 0))
        if need and key in by_type:
            by_type[key].amount -= need
    return True


async def add_resources(session: AsyncSession, planet: Planet, gain: dict[str, float]) -> None:
    """Schreibt EXTERN zugefuehrte Ressourcen gut (Beute, Abbau, Recycling, Transport-Lieferung).

    OGame-Modell: Das Lager-Maximum deckelt NUR die eigene Produktion (Minen stoppen am Cap).
    Von aussen zugefuehrte Rohstoffe duerfen das Lager UEBERFUELLEN (ueber das Maximum hinaus) —
    sie gehen nicht verloren. Die Produktion waechst danach nicht weiter (refresh_resources haelt
    den Ueberschuss, schreibt aber keine Produktion mehr drauf, bis er unter den Cap faellt)."""
    await refresh_resources(session, planet)
    rows = (await session.execute(
        select(Resource).where(
            Resource.planet_id == planet.id,
            Resource.type.in_(RESOURCE_KEYS + EXOTIC_KEYS),
        )
    )).scalars().all()
    by_type = {r.type: r for r in rows}
    for key in RESOURCE_KEYS:
        amount = float(gain.get(key, 0))
        if amount and key in by_type:
            by_type[key].amount = float(by_type[key].amount or 0) + amount
    # Exoten: UNCAPPED gutschreiben (kein Lagergebaeude), Zeile bei Bedarf anlegen.
    for key in EXOTIC_KEYS:
        amount = float(gain.get(key, 0))
        if amount <= 0:
            continue
        row = by_type.get(key)
        if row is not None:
            row.amount = float(row.amount or 0) + amount
        else:
            session.add(Resource(planet_id=planet.id, type=key, amount=amount, rate=0.0))
