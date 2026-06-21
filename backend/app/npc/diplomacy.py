"""Verhandelbare KI-NPC-Imperien (Welle 1, 2026-06-20).

Der Spieler nimmt Kontakt zu einem entdeckten NPC-Imperium auf und VERHANDELT
(Buendnis / Waffenstillstand / Tribut). Die EIGENTLICHE Entscheidung trifft das NPC
emergent per LLM (ai-worker-Job ``npc_decision``) — dieser Code zieht nur die
LEITPLANKEN: Discovery-/Cooldown-Pruefung, Klemmung der Konditionen auf die
balance-Caps, Bestand-/Exploit-Schutz, Statusuebergaenge und die Spiel-Effekte
(Allianz/Waffenstillstand verhindern NPC-Angriffe, Tribut wird periodisch eingezogen).

Die *reinen* Funktionen (``clamp_terms``, ``resolve_terms``, ``apply_decision``,
``relation_blocks_attack``) sind DB-frei und direkt testbar; der ai-worker spiegelt
``resolve_terms``/``apply_decision`` (mit denselben Caps) beim Anwenden der
KI-Entscheidung — Aenderungen hier MUESSEN dort nachgezogen werden.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.npc.attack import fleet_power
from app.platform.balance import Balance, get_balance
from app.platform.models import (
    Fleet,
    NpcEmpire,
    NpcRelation,
    Planet,
    Player,
    PlayerDiscovery,
    PlayerReputation,
    Resource,
    Ship,
)

log = logging.getLogger("universe.npc.diplomacy")

# Vom Spieler waehlbare Angebotsarten.
OFFER_TYPES: tuple[str, ...] = ("alliance", "ceasefire", "tribute")
# Beziehungsstatus, der den Spieler vor NPC-Angriffen schuetzt.
_PROTECTING = ("allied", "ceasefire")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t if t.tzinfo is not None else t.replace(tzinfo=dt.timezone.utc)


def _to_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


# ============================================================================
# Reine Leitplanken-Logik (DB-frei, testbar) — vom ai-worker gespiegelt.
# ============================================================================

def diplomacy_caps(bal: Balance | None = None) -> dict[str, Any]:
    """Liest den balance-Block ``diplomacy`` als flaches Caps-Dict (mit Defaults).

    Dieses Dict wird im Job an den ai-worker uebergeben — die KI sieht ihre Grenzen
    und kann NIE Konditionen jenseits der Caps durchsetzen."""
    d = (bal or get_balance()).data.get("diplomacy", {})
    return {
        "tribute_max": int(d.get("tribute_max", 0)),
        "ceasefire_max_hours": int(d.get("ceasefire_max_hours", 0)),
        "tribute_cycle_hours": int(d.get("tribute_cycle_hours", 24)),
        "negotiate_cooldown_minutes": int(d.get("negotiate_cooldown_minutes", 60)),
        "decision_model": str(d.get("decision_model", "qwen3.5:9b")),
    }


def clamp_terms(
    offer_type: str, terms: dict | None, caps: dict, player_metal: float | None = None
) -> dict[str, int]:
    """Klemmt gewuenschte Konditionen auf die Caps (und den Spieler-Bestand).

    - ``tribute_metal`` <= ``caps.tribute_max`` UND (falls ``player_metal`` gegeben)
      <= aktuell verfuegbares Metall: ein Spieler kann nie mehr zusagen, als er hat.
    - ``ceasefire_hours`` <= ``caps.ceasefire_max_hours``."""
    terms = terms or {}
    trib = max(0, _to_int(terms.get("tribute_metal")))
    trib = min(trib, int(caps.get("tribute_max", 0)))
    if player_metal is not None:
        trib = min(trib, max(0, int(player_metal)))
    hrs = max(0, _to_int(terms.get("ceasefire_hours")))
    hrs = min(hrs, int(caps.get("ceasefire_max_hours", 0)))
    return {"tribute_metal": trib, "ceasefire_hours": hrs}


def resolve_terms(
    offer_type: str,
    choice: str,
    offered_terms: dict | None,
    llm_terms: dict | None,
    caps: dict,
    player_metal: float | None = None,
) -> dict[str, int]:
    """Konditionen, die TATSAECHLICH gelten (accept) bzw. die das NPC GEGEN-anbietet (counter).

    - ``accept`` -> die (geklemmten) Spieler-Konditionen gelten.
    - ``counter`` -> die vom NPC geforderten Konditionen (``tribut_gefordert``/
      ``ceasefire_stunden``), ebenfalls auf die Caps geklemmt.
    - ``reject`` -> keine Konditionen."""
    if choice == "accept":
        return clamp_terms(offer_type, offered_terms, caps, player_metal)
    if choice == "counter":
        proposed = {
            "tribute_metal": (llm_terms or {}).get("tribut_gefordert", 0),
            "ceasefire_hours": (llm_terms or {}).get("ceasefire_stunden", 0),
        }
        # Beim Gegenangebot fordert das NPC Tribut -> NICHT am Spieler-Bestand klemmen
        # (es ist eine Forderung, keine Zusage); nur die harte Cap gilt.
        return clamp_terms(offer_type, proposed, caps, None)
    return {"tribute_metal": 0, "ceasefire_hours": 0}


def apply_decision(
    state: dict, offer_type: str, choice: str, result_terms: dict, now: dt.datetime, caps: dict
) -> dict:
    """Wendet eine ANGENOMMENE Verhandlung auf den Beziehungs-State an (reine Mutation einer Kopie).

    Nur ``accept`` aendert den Status; ``counter``/``reject`` lassen ihn unveraendert
    (das Gegenangebot wartet auf eine erneute Verhandlung des Spielers). Liefert ein
    NEUES State-Dict (Spalten von ``npc_relations``)."""
    s = dict(state)
    s["last_decision_at"] = now
    if choice != "accept":
        return s
    s["positive_actions"] = int(s.get("positive_actions", 0)) + 1
    if offer_type == "alliance":
        s["status"] = "allied"
        s["alliance_since"] = now
        s["ceasefire_until"] = None
        s["tribute_metal_per_cycle"] = 0.0
    elif offer_type == "ceasefire":
        hrs = int(result_terms.get("ceasefire_hours") or 0) or int(caps.get("ceasefire_max_hours", 0))
        s["status"] = "ceasefire"
        s["ceasefire_until"] = now + dt.timedelta(hours=max(1, hrs))
        s["tribute_metal_per_cycle"] = 0.0
    elif offer_type == "tribute":
        cycle = int(caps.get("tribute_cycle_hours", 24))
        s["status"] = "ceasefire"
        s["tribute_metal_per_cycle"] = float(result_terms.get("tribute_metal") or 0)
        s["tribute_last_paid"] = now
        s["ceasefire_until"] = now + dt.timedelta(hours=max(1, cycle))
    return s


def relation_blocks_attack(status: str | None, ceasefire_until: dt.datetime | None, now: dt.datetime) -> bool:
    """True, wenn der aktuelle Beziehungsstatus einen NPC-Angriff verbietet
    (festes Buendnis ODER laufender Waffenstillstand)."""
    if status == "allied":
        return True
    if status == "ceasefire":
        cf = _aware(ceasefire_until)
        return cf is not None and cf > now
    return False


# ============================================================================
# DB-Helfer / Service
# ============================================================================

async def get_or_create_relation(
    session: AsyncSession, player_id: uuid.UUID, npc_id: uuid.UUID
) -> NpcRelation:
    rel = await session.get(NpcRelation, (player_id, npc_id))
    if rel is None:
        rel = NpcRelation(player_id=player_id, npc_id=npc_id, status="neutral")
        session.add(rel)
        await session.flush()
    return rel


async def _player_metal(session: AsyncSession, player_id: uuid.UUID) -> float:
    """Aktuell gelagertes Metall (Summe ueber alle Planeten, gespeicherter Stand)."""
    val = (await session.execute(
        select(func.coalesce(func.sum(Resource.amount), 0.0))
        .join(Planet, Resource.planet_id == Planet.id)
        .where(Planet.player_id == player_id, Resource.type == "metal")
    )).scalar()
    return float(val or 0.0)


async def _player_fleet_power(session: AsyncSession, player_id: uuid.UUID, ship_catalog: dict) -> float:
    """Grober Staerke-Proxy: Summe Angriff*Anzahl ueber Garnison- + fliegende Schiffe."""
    garrison = (await session.execute(
        select(Ship.type, Ship.count)
        .join(Planet, Ship.planet_id == Planet.id)
        .where(Planet.player_id == player_id)
    )).all()
    flying = (await session.execute(
        select(Ship.type, Ship.count)
        .join(Fleet, Ship.fleet_id == Fleet.id)
        .where(Fleet.player_id == player_id)
    )).all()
    fleet: dict[str, int] = {}
    for typ, count in list(garrison) + list(flying):
        fleet[typ] = fleet.get(typ, 0) + int(count or 0)
    return fleet_power(fleet, ship_catalog)


async def _reputation(session: AsyncSession, player_id: uuid.UUID) -> PlayerReputation | None:
    return await session.get(PlayerReputation, player_id)


async def _build_state(
    session: AsyncSession, player: Player, npc: NpcEmpire, rel: NpcRelation, bal: Balance
) -> dict[str, Any]:
    """Strukturierter Spielzustand fuer den LLM-Prompt (Stärkeverhältnis, Lage, Historie, Ruf)."""
    now = _now()
    npc_power = fleet_power(npc.fleet or {}, bal.ships)
    player_power = await _player_fleet_power(session, player.id, bal.ships)
    rep = await _reputation(session, player.id)
    last_atk = _aware(npc.last_attack_at)
    recently_attacked = last_atk is not None and (now - last_atk).total_seconds() < 86400
    return {
        "player_name": player.display_name,
        "player_score": int(player.score or 0),
        "player_fleet_power": round(player_power, 1),
        "npc_fleet_power": round(npc_power, 1),
        # >1 = Spieler staerker, <1 = NPC staerker.
        "strength_ratio": round(player_power / npc_power, 2) if npc_power > 0 else 99.0,
        "npc_resources": {k: int(v) for k, v in (npc.resources or {}).items()},
        "npc_recently_attacked": recently_attacked,
        "relation_status": rel.status,
        "positive_actions": int(rel.positive_actions or 0),
        "negative_actions": int(rel.negative_actions or 0),
        "message_count": int(rel.message_count or 0),
        "betrayed_by_player": bool(rel.betrayed_by_player),
        "betrayed_by_npc": bool(rel.betrayed_by_npc),
        "current_tribute_metal_per_cycle": int(rel.tribute_metal_per_cycle or 0),
        # Spieler-RUF (Verrate an ANDEREN NPCs) — ein stolzes Imperium straft Verraeter.
        "player_betrayals": int(rep.betrayals if rep else 0),
        "player_alliances_honored": int(rep.alliances_honored if rep else 0),
    }


async def initiate_negotiation(
    session: AsyncSession, player: Player, npc: NpcEmpire, offer_type: str,
    terms: dict | None, message: str | None = None,
) -> dict[str, Any]:
    """Startet eine Verhandlung: prueft Discovery + Cooldown, klemmt die Konditionen und
    reiht den KI-Entscheidungs-Job ein. Wirft ``ValueError`` mit Fehlercode bei Verstoessen
    (der Router uebersetzt das in HTTP)."""
    from app.platform.ai_jobs import enqueue_npc_decision

    if offer_type not in OFFER_TYPES:
        raise ValueError("invalid_offer_type")

    bal = get_balance()
    caps = diplomacy_caps(bal)
    now = _now()

    # 1) Discovery: nur ein dem Spieler BEKANNTES Imperium ist ansprechbar.
    discovered = (await session.execute(
        select(PlayerDiscovery.player_id).where(
            PlayerDiscovery.player_id == player.id,
            PlayerDiscovery.galaxy == npc.galaxy,
            PlayerDiscovery.system == npc.system,
            PlayerDiscovery.position == npc.position,
        )
    )).scalar_one_or_none()
    if discovered is None:
        raise ValueError("not_discovered")

    rel = await get_or_create_relation(session, player.id, npc.id)

    # 2) Cooldown: Spam unterbinden (auch waehrend eine Entscheidung in Arbeit ist —
    #    last_decision_at wird hier provisorisch gesetzt).
    last = _aware(rel.last_decision_at)
    cooldown_s = caps["negotiate_cooldown_minutes"] * 60
    if last is not None and (now - last).total_seconds() < cooldown_s:
        raise ValueError("cooldown")

    # 3) Spieler-Konditionen klemmen (Bestand-Schutz beim Tribut).
    metal = await _player_metal(session, player.id)
    offered = clamp_terms(offer_type, terms, caps, metal)

    rel.message_count = int(rel.message_count or 0) + 1
    rel.last_decision_at = now  # Cooldown-Anker + In-Flight-Schutz

    state = await _build_state(session, player, npc, rel, bal)
    # Spieler-Freitext als DATEN mitgeben (im Prompt strikt von Instruktionen getrennt).
    if message:
        state["player_message"] = str(message)[:600]

    await enqueue_npc_decision(
        npc_id=npc.id, player_id=player.id,
        offer_type=offer_type, offered_terms=offered, caps=caps, state=state,
    )
    log.info("Verhandlung eingereicht: player=%s npc=%s offer=%s terms=%s",
             player.id, npc.id, offer_type, offered)
    return {"status": rel.status, "offered_terms": offered}


async def break_pact(session: AsyncSession, player: Player, npc: NpcEmpire) -> NpcRelation:
    """Spieler bricht einen bestehenden Pakt (Verrat). Setzt ``betrayed_by_player``, macht das
    NPC feindlich und erhoeht den globalen Verrats-Ruf des Spielers (W3/Chronik). Idempotent
    genug: ohne aktiven Pakt aendert sich nur der Status auf 'hostile'."""
    rel = await get_or_create_relation(session, player.id, npc.id)
    was_pact = rel.status in _PROTECTING
    rel.status = "hostile"
    rel.betrayed_by_player = True
    rel.broken_at = _now()
    rel.ceasefire_until = None
    rel.alliance_since = None
    rel.tribute_metal_per_cycle = 0.0
    rel.negative_actions = int(rel.negative_actions or 0) + 1
    if was_pact:
        rep = await _reputation(session, player.id)
        if rep is None:
            rep = PlayerReputation(player_id=player.id, betrayals=0, alliances_honored=0)
            session.add(rep)
        rep.betrayals = int(rep.betrayals or 0) + 1
        rep.updated_at = _now()
    log.info("Pakt gebrochen: player=%s npc=%s (war_pakt=%s)", player.id, npc.id, was_pact)
    return rel


async def protected_player_ids_for_npc(session: AsyncSession, npc_id: uuid.UUID) -> set[uuid.UUID]:
    """Spieler, die DIESES NPC wegen Buendnis/aktivem Waffenstillstand NICHT angreifen darf."""
    now = _now()
    rows = (await session.execute(
        select(NpcRelation.player_id, NpcRelation.status, NpcRelation.ceasefire_until)
        .where(NpcRelation.npc_id == npc_id, NpcRelation.status.in_(_PROTECTING))
    )).all()
    return {pid for pid, status, cf in rows if relation_blocks_attack(status, cf, now)}


# ----------------------------------------------------------------- Tribut-Tick

async def tribute_tick() -> None:
    """Periodischer Job: zieht faelligen Tribut ein. Kann der Spieler nicht zahlen, bricht der
    Pakt (NPC fuehlt sich betrogen -> hostile, betrayed_by_player). Sonst wandert das Metall ins
    NPC-Lager und der Waffenstillstand wird um einen Zyklus verlaengert."""
    from app.economy.service import refresh_resources
    from app.messaging.service import create_system_transmission

    bal = get_balance()
    caps = diplomacy_caps(bal)
    cycle = dt.timedelta(hours=caps["tribute_cycle_hours"])
    now = _now()
    from app.platform.db import session_scope

    processed = 0
    async with session_scope() as session:
        rels = (await session.execute(
            select(NpcRelation).where(
                NpcRelation.tribute_metal_per_cycle > 0,
                NpcRelation.status == "ceasefire",
            )
        )).scalars().all()
        for rel in rels:
            last_paid = _aware(rel.tribute_last_paid)
            if last_paid is not None and (now - last_paid) < cycle:
                continue  # Zyklus noch nicht um
            amount = float(rel.tribute_metal_per_cycle or 0)
            npc = await session.get(NpcEmpire, rel.npc_id)
            player = await session.get(Player, rel.player_id)
            if npc is None or player is None:
                continue

            # Verfuegbares Metall (frisch hochgerechnet) ueber die Planeten sammeln.
            planets = (await session.execute(
                select(Planet).where(Planet.player_id == rel.player_id)
            )).scalars().all()
            for p in planets:
                await refresh_resources(session, p)
            res_rows = (await session.execute(
                select(Resource)
                .join(Planet, Resource.planet_id == Planet.id)
                .where(Planet.player_id == rel.player_id, Resource.type == "metal")
            )).scalars().all()
            available = sum(float(r.amount or 0) for r in res_rows)

            if available < amount:
                # Zahlungsausfall = Vertragsbruch durch den Spieler.
                rel.status = "hostile"
                rel.betrayed_by_player = True
                rel.broken_at = now
                rel.tribute_metal_per_cycle = 0.0
                rel.ceasefire_until = None
                rel.negative_actions = int(rel.negative_actions or 0) + 1
                rep = await _reputation(session, rel.player_id)
                if rep is None:
                    rep = PlayerReputation(player_id=rel.player_id, betrayals=0, alliances_honored=0)
                    session.add(rep)
                rep.betrayals = int(rep.betrayals or 0) + 1
                rep.updated_at = now
                await create_system_transmission(
                    session, player_id=rel.player_id,
                    subject=f"{npc.name}: Tribut nicht geleistet",
                    body=(f"Du konntest den vereinbarten Tribut ({int(amount)} Metall) an {npc.name} "
                          f"nicht aufbringen. Der Waffenstillstand ist gebrochen — das Imperium ist "
                          f"nun feindlich gesinnt."),
                    ttype="npc_diplomacy",
                )
                processed += 1
                continue

            # Tribut greedy von den Planeten abziehen.
            remaining = amount
            for r in res_rows:
                if remaining <= 0:
                    break
                take = min(float(r.amount or 0), remaining)
                r.amount = float(r.amount or 0) - take
                remaining -= take
            nres = dict(npc.resources or {})
            nres["metal"] = float(nres.get("metal", 0)) + amount
            npc.resources = nres
            rel.tribute_last_paid = now
            rel.ceasefire_until = now + cycle
            rel.positive_actions = int(rel.positive_actions or 0) + 1
            processed += 1
    if processed:
        log.info("Tribut-Tick: %d Beziehungen verarbeitet", processed)
