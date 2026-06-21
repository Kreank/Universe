"""Die erwachende Galaxie (Welle 4) — Aggressions-Metrik + Wächter-Lebenszyklus.

Kern-Idee (Sascha): Ein uralter Wächter reagiert auf das GESAMT-Aggressionsniveau ALLER
Spieler. Zu viel Krieg weckt eine server-weite Bedrohung, die alle zwingt, kurz innezuhalten
und zusammenzuhalten; sein Besiegen beruhigt das Universum + belohnt — ein lebendiges,
emergentes Selbstregulativ.

Architektur:
- Die REINE/testbare Bewertungslogik (``compute_aggression_level``, ``aggression_status``,
  ``should_awaken``, ``compute_warden_fleet``) ist DB-/LLM-frei.
- ``aggression_tick`` (stündlich, Scheduler) aggregiert die ``combat_reports`` des Fensters,
  schreibt eine ``aggression_history``-Zeile und treibt den Wächter-Lebenszyklus:
  erwachen (Schwelle überschritten) → bedrohen/angreifen (telegrafiert) → besiegt/zurückgezogen.
- Der KAMPF-Körper des Wächters ist ein ``NpcEmpire`` (behavior_profile ``warden``): so wird der
  bestehende Spieler<->NPC-Kampf (combat/service) UND die ausgehende ``NpcAttack``-Infrastruktur
  wiederverwendet. Die ``awakening_warden``-Zeile hält nur den server-weiten Lebenszyklus-Zustand.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import (
    AggressionHistory,
    AwakeningWarden,
    CombatReport,
    NpcEmpire,
    Planet,
    Player,
    Resource,
)
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.awakening")

_RESOURCE_KEYS = ("metal", "crystal", "deuterium")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t if t.tzinfo is not None else t.replace(tzinfo=dt.timezone.utc)


# ============================================================================
# REINE, testbare Logik (DB-/LLM-frei).
# ============================================================================

def aggression_status(level: float, cfg: dict) -> str:
    """Bildet einen Aggressions-Level auf sein Status-Band ab (höchstes ``min`` <= level gewinnt).

    ``cfg.status_bands`` = [{"status": "peaceful", "min": 0}, ...]. Fallback: 'peaceful'."""
    bands = cfg.get("status_bands") or []
    status = "peaceful"
    best_min = float("-inf")
    for band in bands:
        m = float(band.get("min", 0))
        if level >= m and m >= best_min:
            status = str(band.get("status", status))
            best_min = m
    return status


def compute_aggression_level(
    combat_count: int, total_debris: float, unique_attackers: int, cfg: dict
) -> tuple[float, str]:
    """Gewichteter Gesamt-Aggressionswert des Universums + Status-Band (REIN, testbar).

    level = combat_count*w.combat + total_debris*w.debris + unique_attackers*w.attackers."""
    w = cfg.get("weights", {})
    level = (
        float(combat_count) * float(w.get("combat", 0))
        + float(total_debris) * float(w.get("debris", 0))
        + float(unique_attackers) * float(w.get("attackers", 0))
    )
    return level, aggression_status(level, cfg)


def should_awaken(
    level: float, threshold: float, has_active_warden: bool,
    calm_until: dt.datetime | None, now: dt.datetime,
) -> bool:
    """Reine Entscheidung, ob ein (neuer) Wächter erwachen soll.

    Kein Doppel-Spawn bei aktivem Wächter; während der Beruhigungsphase (``calm_until`` in der
    Zukunft, nach Niederlage/Rückzug) erwacht trotz hoher Aggression keiner — das beruhigte
    Universum bekommt Luft (Selbstregulativ)."""
    if has_active_warden:
        return False
    cu = _aware(calm_until)
    if cu is not None and cu > now:
        return False
    return level >= threshold


def compute_warden_fleet(level: float, top_scores: list[float], cfg: dict) -> dict[str, int]:
    """Skaliert die Wächter-Flotte mit dem Aggressionsniveau UND der Stärke der Top-Spieler (REIN).

    - Multiplikator = clamp(level/threshold, 1 .. max_fleet_mult) — stärkere Eskalation = stärkerer Wächter.
    - Top-Spieler-Bonus = (1 + fleet_top_player_scale * Summe(top_scores)) — wächst mit dem Server.
    - ``fleet_per_level`` addiert pro Schiffstyp Einheiten je Aggressionspunkt ÜBER der Schwelle.
    Bei ``level == threshold`` und ohne Top-Spieler ergibt sich exakt ``warden.base_fleet``."""
    warden = cfg.get("warden", {})
    base = warden.get("base_fleet", {}) or {}
    threshold = float(cfg.get("threshold", 0)) or 1.0
    max_mult = float(warden.get("max_fleet_mult", 1e9))
    mult = min(max_mult, max(1.0, float(level) / threshold))
    top_sum = sum(float(s) for s in (top_scores or []))
    top_mult = 1.0 + float(warden.get("fleet_top_player_scale", 0)) * top_sum
    over = max(0.0, float(level) - threshold)
    per_level = warden.get("fleet_per_level", {}) or {}

    fleet: dict[str, int] = {}
    for typ, count in base.items():
        scaled = float(count) * mult * top_mult + float(per_level.get(typ, 0)) * over
        n = int(round(scaled))
        if n > 0:
            fleet[typ] = n
    return fleet


# ============================================================================
# DB-Aggregation + Wächter-Lebenszyklus.
# ============================================================================

async def _gather_aggression(session: AsyncSession, cutoff: dt.datetime) -> tuple[int, float, int, Counter]:
    """Aggregiert die combat_reports seit ``cutoff``: (Kampfanzahl, Gesamt-Trümmer,
    eindeutige Angreifer, Counter attacker_id->Anzahl). Trümmer = Metall+Kristall je Bericht."""
    reports = (await session.execute(
        select(CombatReport).where(CombatReport.created_at >= cutoff)
    )).scalars().all()
    total_debris = 0.0
    attackers: Counter = Counter()
    for rep in reports:
        d = rep.debris or {}
        total_debris += float(d.get("metal", 0)) + float(d.get("crystal", 0))
        if rep.attacker_id is not None:
            attackers[rep.attacker_id] += 1
    return len(reports), total_debris, len(attackers), attackers


async def _record_history(
    session: AsyncSession, hour: dt.datetime,
    combat_count: int, total_debris: float, unique_attackers: int,
    level: float, status: str,
) -> None:
    """Upsert der Aggressions-Zeile für die aktuelle volle Stunde (idempotent je Stunde)."""
    row = await session.get(AggressionHistory, hour)
    if row is None:
        session.add(AggressionHistory(
            hour=hour, combat_count=combat_count, total_debris=total_debris,
            unique_attackers=unique_attackers, level=level, status=status,
        ))
    else:
        row.combat_count = combat_count
        row.total_debris = total_debris
        row.unique_attackers = unique_attackers
        row.level = level
        row.status = status


async def _active_warden(session: AsyncSession) -> AwakeningWarden | None:
    return (await session.execute(
        select(AwakeningWarden).where(AwakeningWarden.status == "active")
        .order_by(AwakeningWarden.spawned_at.desc()).limit(1)
    )).scalar_one_or_none()


async def _latest_calm_until(session: AsyncSession) -> dt.datetime | None:
    """Jüngster Beruhigungs-Cooldown (egal welcher Status) — verhindert Sofort-Re-Spawn."""
    return (await session.execute(
        select(func.max(AwakeningWarden.calm_until))
    )).scalar_one_or_none()


async def _top_player_scores(session: AsyncSession, limit: int = 5) -> list[float]:
    rows = (await session.execute(
        select(Player.score).order_by(Player.score.desc()).limit(limit)
    )).scalars().all()
    return [float(s or 0) for s in rows]


# -- Erwachen ----------------------------------------------------------------

async def awaken_warden(session: AsyncSession, level: float) -> AwakeningWarden | None:
    """Erweckt den Wächter: legt den NpcEmpire-Kampfkörper + die awakening_warden-Zeile an,
    kündigt ihn server-weit an (Broadcast + KI-Funkspruch, Narrator 'warden') und telegrafiert
    die Vorwarnzeit, bevor er angreift. Liefert die Zeile (oder None, wenn kein Ort frei)."""
    cfg = get_balance().awakening
    wcfg = cfg.get("warden", {})

    # Standort: eine möglichst freie, prominente Koordinate (Wiederverwendung events._free_coords).
    from app.events.service import _free_coords
    coords = await _free_coords(session, get_balance())
    if coords is None:
        log.warning("Wächter konnte nicht erwachen: keine freie Koordinate gefunden")
        return None
    g, s, p = coords

    fleet = compute_warden_fleet(level, await _top_player_scores(session), cfg)
    defenses = dict(wcfg.get("defenses", {}) or {})
    name = str(wcfg.get("name", "Der Erwachte"))

    npc = NpcEmpire(
        name=name,
        behavior_profile="warden",  # vom NPC-Behavior/Decay-/Populations-Tick ausgenommen
        galaxy=g, system=s, position=p,
        fleet=dict(fleet), defenses=defenses, resources={},
        baseline={},  # KEIN Wiederaufbau (Wächter heilt nicht zwischen Angriffen)
        persona={
            "named": True,
            "background": "Ein uralter Wächter aus der Zeit vor den Imperien, erwacht durch das "
                          "Übermaß an Krieg im Universum.",
            "voice": "würdevoll, uralt, bedrohlich-ruhig",
        },
        last_action_at=_now(),
    )
    session.add(npc)
    await session.flush()
    from app.universe.service import occupy_cell
    await occupy_cell(session, g, s, p, "npc", npc.id)

    now = _now()
    warning_h = float(cfg.get("warning_hours", 4))
    lifetime_h = float(cfg.get("lifetime_hours", 72))
    threats_after = now + dt.timedelta(hours=warning_h)
    warden = AwakeningWarden(
        npc_id=npc.id, aggression_level=float(level), fleet=dict(fleet),
        target_scope="global", status="active",
        spawned_at=now, expires_at=now + dt.timedelta(hours=lifetime_h),
        data={"participants": [], "threats": 0, "threats_after": threats_after.isoformat(),
              "coords": f"{g}:{s}:{p}"},
    )
    session.add(warden)
    await session.flush()

    coord_str = f"{g}:{s}:{p}"
    total_ships = int(sum(fleet.values()))
    await _broadcast(
        session,
        subject="⚠️ DER ERWACHTE regt sich",
        body=(f"Etwas Uraltes ist im Übermaß des Krieges erwacht. Bei {coord_str} sammelt sich eine "
              f"gewaltige Streitmacht ({total_ships} Schiffe). In etwa {int(warning_h)} Stunden wird "
              f"„{name}\" über die aggressivsten Imperien herfallen. Haltet inne — oder schließt euch "
              f"zusammen und stellt euch ihm bei {coord_str}, um das Universum zu beruhigen."),
    )

    # KI-Ankündigung (würdevoll-bedrohlich, Narrator 'warden', qwen think=false). Best-effort.
    try:
        from app.platform.ai_jobs import enqueue_flavor
        await enqueue_flavor(
            narrator="warden", broadcast=True, ttype="system",
            situation="Erwachen aus uraltem Schlaf, ausgelöst durch das Übermaß an Krieg",
            planet=coord_str,
            detail={
                "Aggressionsniveau des Universums": int(level),
                "Ort der Sammlung": coord_str,
                "Stunden bis zum ersten Zorn": int(warning_h),
            },
            model=str(wcfg.get("model", "qwen3.5:9b")), think=False,
        )
    except Exception:  # noqa: BLE001 — Funkspruch darf das Erwachen nie verhindern
        log.exception("Wächter-Ankündigung (KI) fehlgeschlagen")

    log.info("Wächter erwacht @ %s (level=%.1f, %d Schiffe)", coord_str, level, total_ships)
    return warden


# -- Bedrohung / Angriff (telegrafiert, fair) --------------------------------

async def _most_aggressive_players(session: AsyncSession, attackers: Counter, limit: int) -> list[uuid.UUID]:
    """Die aktivsten Angreifer des Fensters (nach Angriffsanzahl), nur echte, angreifbare Spieler."""
    if not attackers:
        return []
    ids = [pid for pid, _ in attackers.most_common()]
    rows = (await session.execute(
        select(Player.id, Player.is_protected, Player.vacation_until).where(Player.id.in_(ids))
    )).all()
    now = _now()
    ok: dict[uuid.UUID, bool] = {}
    for pid, prot, vac in rows:
        vac = _aware(vac)
        ok[pid] = (not prot) and (vac is None or vac <= now)
    out = [pid for pid in ids if ok.get(pid)]
    return out[:limit]


async def _launch_warden_attack(
    session: AsyncSession, npc: NpcEmpire, target_player_id: uuid.UUID, cfg: dict,
) -> bool:
    """Entsendet eine Teil-Flotte des Wächters gegen einen Spieler-Planeten (reuse NpcAttack).

    Telegrafiert (min_warning_hours Vorwarnung), zieht die Schiffe aus der Garnison ab und plant
    die Auflösung (resolve_npc_attack — Spieler ist Verteidiger). True bei Start."""
    from app.fleet.service import compute_distance, flight_seconds, slowest_ship_speed
    from app.messaging.service import create_system_transmission
    from app.npc.attack import resolve_npc_attack, select_commit_fleet
    from app.platform.models import NpcAttack

    # Ziel: ein (nicht-Mond-) Planet des Spielers (Heimat bevorzugt).
    target = (await session.execute(
        select(Planet).where(Planet.player_id == target_player_id, Planet.planet_type != "moon")
        .order_by(Planet.is_homeworld.desc(), Planet.created_at.asc()).limit(1)
    )).scalars().first()
    if target is None:
        return False

    # Kein zweiter gleichzeitiger Wächter-Angriff auf denselben Spieler.
    existing = (await session.execute(
        select(NpcAttack.id).where(
            NpcAttack.npc_id == npc.id, NpcAttack.target_player_id == target_player_id,
            NpcAttack.status == "incoming",
        ).limit(1)
    )).first()
    if existing is not None:
        return False

    commit = select_commit_fleet(npc.fleet or {}, float(cfg.get("threat", {}).get("commit_fraction", 0.2)))
    if not commit:
        return False

    garrison = dict(npc.fleet or {})
    for typ, count in commit.items():
        garrison[typ] = garrison.get(typ, 0) - count
        if garrison[typ] <= 0:
            garrison.pop(typ, None)
    npc.fleet = garrison

    from app.platform.balance import get_balance as _gb
    bal = _gb()
    distance = compute_distance((npc.galaxy, npc.system, npc.position),
                                (target.galaxy, target.system, target.position))
    min_warn = float(cfg.get("threat", {}).get("min_warning_hours", 2)) * 3600.0
    secs = max(flight_seconds(distance, slowest_ship_speed(commit), bal.fleet_speed), min_warn)
    arrive = _now() + dt.timedelta(seconds=secs)

    atk = NpcAttack(
        npc_id=npc.id, target_player_id=target_player_id, target_planet_id=target.id,
        target_galaxy=target.galaxy, target_system=target.system, target_position=target.position,
        fleet=dict(commit), status="incoming", arrive_at=arrive,
        data={"warden": True},
    )
    session.add(atk)
    await session.flush()
    npc.last_attack_at = _now()
    schedule_at(arrive, resolve_npc_attack, str(atk.id), job_id=f"npc-attack:{atk.id}")

    loc = f"{target.galaxy}:{target.system}:{target.position}"
    await create_system_transmission(
        session, player_id=target_player_id,
        subject="⚠️ DER ERWACHTE kommt für dich",
        body=(f"Der uralte Wächter hat dein Übermaß an Krieg bemerkt. Eine seiner Streitmächten "
              f"({int(sum(commit.values()))} Schiffe) nähert sich {loc}. Eintreffen in ca. "
              f"{int(secs // 3600)} Std {int((secs % 3600) // 60)} Min. Bereite dich vor — oder "
              f"verbünde dich."),
        ttype="system",
    )
    log.info("Wächter greift Spieler %s an -> %s (ETA %ds)", target_player_id, loc, int(secs))
    return True


async def _run_warden_threats(
    session: AsyncSession, warden: AwakeningWarden, npc: NpcEmpire, attackers: Counter, cfg: dict,
) -> None:
    """Pro Tick: bedroht die aggressivsten Spieler (telegrafierte Angriffe) + KI-Funkspruch."""
    tcfg = cfg.get("threat", {})
    now = _now()

    # Vorwarnphase: vor 'threats_after' (= Erwachen + warning_hours) greift er noch nicht an.
    data = dict(warden.data or {})
    threats_after = _aware_iso(data.get("threats_after"))
    if threats_after is not None and now < threats_after:
        return
    # Eigener Angriffs-Cooldown zwischen Bedrohungswellen.
    last = _aware(warden.last_threat_at)
    cooldown_h = float(tcfg.get("cooldown_hours", 6))
    if last is not None and (now - last).total_seconds() < cooldown_h * 3600.0:
        return

    targets = await _most_aggressive_players(session, attackers, int(tcfg.get("targets_per_tick", 2)))
    launched = 0
    for pid in targets:
        try:
            if await _launch_warden_attack(session, npc, pid, cfg):
                launched += 1
        except Exception:  # noqa: BLE001 — ein fehlgeschlagener Angriff darf den Tick nicht killen
            log.exception("Wächter-Angriff auf %s fehlgeschlagen", pid)

    if launched > 0:
        warden.last_threat_at = now
        data["threats"] = int(data.get("threats", 0)) + launched
        warden.data = data
        # KI-Funkspruch (würdevoll-bedrohlich). Best-effort.
        try:
            from app.platform.ai_jobs import enqueue_flavor
            await enqueue_flavor(
                narrator="warden", broadcast=True, ttype="system",
                situation="Der Wächter erhebt sich gegen die kriegerischsten Imperien",
                planet=str((warden.data or {}).get("coords") or f"{npc.galaxy}:{npc.system}:{npc.position}"),
                detail={"Ziele dieser Welle": launched},
                model=str(cfg.get("warden", {}).get("model", "qwen3.5:9b")), think=False,
            )
        except Exception:  # noqa: BLE001
            log.exception("Wächter-Funkspruch (Bedrohung) fehlgeschlagen")


# -- Besiegen / Rückzug ------------------------------------------------------

async def note_warden_combat(
    session: AsyncSession, npc: NpcEmpire, attacker_player_id, winner: str,
) -> None:
    """Combat-Hook (best-effort, aus combat/service): verbucht einen Spieler als Wächter-Teilnehmer
    und löst — wenn der Wächter-Kampfkörper restlos zerschlagen ist — ``defeat_warden`` aus.

    Idempotent: ``defeat_warden`` prüft den Status. Wird NUR aufgerufen, wenn der Verteidiger der
    Wächter-NPC ist (behavior_profile 'warden')."""
    warden = (await session.execute(
        select(AwakeningWarden).where(
            AwakeningWarden.npc_id == npc.id, AwakeningWarden.status == "active"
        ).limit(1)
    )).scalar_one_or_none()
    if warden is None:
        return

    if attacker_player_id is not None:
        data = dict(warden.data or {})
        parts = list(data.get("participants", []))
        pid_str = str(attacker_player_id)
        if pid_str not in parts:
            parts.append(pid_str)
            data["participants"] = parts
            warden.data = data

    # Restlos zerschlagen? (Flotte + Verteidigung leer.)
    fleet_left = sum(int(v) for v in (npc.fleet or {}).values())
    def_left = sum(int(v) for v in (npc.defenses or {}).values())
    if fleet_left <= 0 and def_left <= 0:
        # WICHTIG: den NPC NICHT hier loeschen — combat/service nutzt ihn nach diesem Hook noch
        # (Funkspruch npc_reaction mit FK npc_id). Die leere Huelle wird im naechsten
        # aggression_tick via _sweep_warden_husks aufgeraeumt.
        await defeat_warden(session, warden, remove_npc=False)


async def defeat_warden(
    session: AsyncSession, warden: AwakeningWarden, *, remove_npc: bool = True,
) -> None:
    """Der Wächter ist besiegt: belohnt alle Teilnehmer, kündigt den Sieg server-weit an,
    beruhigt das Universum (calm_until = now + respawn_dormant_hours) und setzt ihn dormant.
    ``remove_npc`` entfernt den NPC-Kampfkörper + gibt die Zelle frei (False aus dem Combat-Hook,
    wo der NPC nach dem Aufruf noch gebraucht wird -> Aufräumen via _sweep_warden_husks).
    Idempotent (Status-Guard)."""
    if warden.status != "active":
        return
    cfg = get_balance().awakening
    reward = cfg.get("reward", {})
    now = _now()

    participants = list((warden.data or {}).get("participants", []))
    rewarded = 0
    for pid_str in participants:
        try:
            pid = uuid.UUID(str(pid_str))
        except (ValueError, TypeError):
            continue
        home = (await session.execute(
            select(Planet).where(Planet.player_id == pid, Planet.planet_type != "moon")
            .order_by(Planet.is_homeworld.desc(), Planet.created_at.asc()).limit(1)
        )).scalars().first()
        if home is None:
            continue
        res_rows = (await session.execute(
            select(Resource).where(Resource.planet_id == home.id, Resource.type.in_(_RESOURCE_KEYS))
        )).scalars().all()
        by_type = {r.type: r for r in res_rows}
        for key in _RESOURCE_KEYS:
            amt = float(reward.get(key, 0))
            if amt <= 0:
                continue
            if key in by_type:
                by_type[key].amount = float(by_type[key].amount) + amt
            else:
                session.add(Resource(planet_id=home.id, type=key, amount=amt, rate=0.0))
        dm = float(reward.get("dark_matter", 0))
        if dm > 0:
            player = await session.get(Player, pid)
            if player is not None:
                player.dark_matter = float(player.dark_matter or 0) + dm
        from app.messaging.service import create_system_transmission
        await create_system_transmission(
            session, player_id=pid,
            subject="🏆 Der Wächter ist besiegt — deine Belohnung",
            body=(f"Du standst dem Erwachten gegenüber und hast mitgeholfen, ihn zu bezwingen. "
                  f"Als Dank empfängt dein Heimatplanet {int(reward.get('metal', 0))} Metall, "
                  f"{int(reward.get('crystal', 0))} Kristall, {int(reward.get('deuterium', 0))} "
                  f"Deuterium" + (f" und {int(dm)} Dunkle Materie" if dm > 0 else "") + ". "
                  "Das Universum atmet auf."),
            ttype="big_moment",
        )
        rewarded += 1

    # NPC-Kampfkörper entfernen + Zelle freigeben (nur wenn er hier nicht mehr gebraucht wird).
    if remove_npc and warden.npc_id is not None:
        npc = await session.get(NpcEmpire, warden.npc_id)
        if npc is not None:
            try:
                from app.universe.service import vacate_cell
                await vacate_cell(session, npc.galaxy, npc.system, npc.position)
            except Exception:  # noqa: BLE001
                log.exception("Zelle des besiegten Wächters konnte nicht freigegeben werden")
            await session.delete(npc)

    warden.status = "defeated"
    warden.defeated_at = now
    warden.calm_until = now + dt.timedelta(hours=float(cfg.get("respawn_dormant_hours", 48)))

    await _broadcast(
        session,
        subject="🌌 DER ERWACHTE ist besiegt",
        body=("Die Imperien haben innegehalten, sich zusammengetan und den uralten Wächter "
              "bezwungen. Eine Welle der Ruhe legt sich über das Universum — der Krieg möge "
              "für eine Weile schweigen."),
    )
    try:
        from app.platform.ai_jobs import enqueue_flavor
        await enqueue_flavor(
            narrator="warden", broadcast=True, ttype="system",
            situation="Niederlage und Rückzug in den Schlaf, nachdem die Imperien sich vereinten",
            detail={"Teilnehmer, die ihn bezwangen": rewarded},
            model=str(cfg.get("warden", {}).get("model", "qwen3.5:9b")), think=False,
        )
    except Exception:  # noqa: BLE001
        log.exception("Wächter-Funkspruch (Niederlage) fehlgeschlagen")
    log.info("Wächter besiegt (%d Teilnehmer belohnt), Universum beruhigt bis %s",
             rewarded, warden.calm_until)


async def retreat_warden(session: AsyncSession, warden: AwakeningWarden) -> None:
    """Lebenszeit abgelaufen, ohne besiegt zu werden: der Wächter zieht sich in den Schlaf zurück.
    Beruhigt das Universum ebenfalls (kürzere/normale Cooldown-Phase) und setzt ihn dormant."""
    if warden.status != "active":
        return
    cfg = get_balance().awakening
    now = _now()
    if warden.npc_id is not None:
        npc = await session.get(NpcEmpire, warden.npc_id)
        if npc is not None:
            try:
                from app.universe.service import vacate_cell
                await vacate_cell(session, npc.galaxy, npc.system, npc.position)
            except Exception:  # noqa: BLE001
                log.exception("Zelle des zurückgezogenen Wächters konnte nicht freigegeben werden")
            await session.delete(npc)
    warden.status = "dormant"
    warden.defeated_at = now
    warden.calm_until = now + dt.timedelta(hours=float(cfg.get("respawn_dormant_hours", 48)))
    await _broadcast(
        session,
        subject="🌑 DER ERWACHTE zieht sich zurück",
        body=("Der uralte Wächter hat sein Urteil gefällt und sinkt zurück in den Schlaf der "
              "Äonen. Doch er wacht — bändigt euren Krieg, sonst kehrt er wieder."),
    )
    log.info("Wächter zog sich zurück (nicht besiegt), Universum beruhigt bis %s", warden.calm_until)


# -- Broadcast-Helfer (Muster: events.service._announce) ---------------------

async def _broadcast(session: AsyncSession, *, subject: str, body: str) -> None:
    """Server-weites Bulletin an alle Spieler (ein Funkspruch je Spieler)."""
    from app.messaging.service import create_system_transmission
    player_ids = (await session.execute(select(Planet.player_id).distinct())).scalars().all()
    for pid in player_ids:
        await create_system_transmission(
            session, player_id=pid, subject=subject, body=body, ttype="system", publish=False,
        )


async def _sweep_warden_husks(session: AsyncSession) -> int:
    """Räumt leere Wächter-NPC-Hüllen auf: alle NpcEmpires mit behavior_profile 'warden', die
    von KEINER aktiven awakening_warden-Zeile mehr referenziert werden (z.B. nach einem im
    Kampf besiegten Wächter, dessen NPC im Combat-Hook bewusst nicht gelöscht wurde)."""
    active_ids = set((await session.execute(
        select(AwakeningWarden.npc_id).where(AwakeningWarden.status == "active")
    )).scalars().all())
    husks = (await session.execute(
        select(NpcEmpire).where(NpcEmpire.behavior_profile == "warden")
    )).scalars().all()
    removed = 0
    for npc in husks:
        if npc.id in active_ids:
            continue
        try:
            from app.universe.service import vacate_cell
            await vacate_cell(session, npc.galaxy, npc.system, npc.position)
        except Exception:  # noqa: BLE001
            log.exception("Zelle einer Wächter-Hülle konnte nicht freigegeben werden")
        await session.delete(npc)
        removed += 1
    if removed:
        log.info("Wächter-Hüllen aufgeräumt: %d", removed)
    return removed


def _aware_iso(value) -> dt.datetime | None:
    if not value:
        return None
    try:
        return _aware(dt.datetime.fromisoformat(str(value)))
    except (ValueError, TypeError):
        return None


# ============================================================================
# Stündlicher Scheduler-Tick.
# ============================================================================

async def aggression_tick() -> None:
    """Stündlich: Aggressions-Metrik aggregieren + Wächter-Lebenszyklus treiben.

    1. combat_reports des Fensters → aggression_history-Zeile (level + status).
    2. Aktiver Wächter? → abgelaufen → retreat; sonst Bedrohungswelle treiben.
    3. Kein Wächter + Schwelle überschritten + keine Beruhigungsphase → awaken_warden."""
    cfg = get_balance().awakening
    if not cfg.get("enabled", False):
        return

    lookback_h = float(cfg.get("lookback_hours", 6))
    threshold = float(cfg.get("threshold", 1e9))
    now = _now()
    cutoff = now - dt.timedelta(hours=lookback_h)
    hour = now.replace(minute=0, second=0, microsecond=0)

    async with session_scope() as session:
        combat_count, total_debris, unique_attackers, attackers = await _gather_aggression(session, cutoff)
        level, status = compute_aggression_level(combat_count, total_debris, unique_attackers, cfg)
        await _record_history(session, hour, combat_count, total_debris, unique_attackers, level, status)

        # Leere Wächter-Hüllen aus im Kampf besiegten Wächtern aufräumen (Combat-Hook löscht den
        # NPC nicht selbst). Best-effort; darf den Tick nicht killen.
        try:
            await _sweep_warden_husks(session)
        except Exception:  # noqa: BLE001
            log.exception("Wächter-Hüllen-Sweep fehlgeschlagen")

        warden = await _active_warden(session)
        if warden is not None:
            expires = _aware(warden.expires_at)
            if expires is not None and expires <= now:
                await retreat_warden(session, warden)
            else:
                npc = await session.get(NpcEmpire, warden.npc_id) if warden.npc_id else None
                if npc is None:
                    # Kampfkörper verschwunden (z.B. vollständig zerschlagen+entfernt) -> besiegt.
                    await defeat_warden(session, warden)
                else:
                    await _run_warden_threats(session, warden, npc, attackers, cfg)
        else:
            calm_until = await _latest_calm_until(session)
            if should_awaken(level, threshold, False, calm_until, now):
                await awaken_warden(session, level)

        await session.commit()
    log.info("Aggressions-Tick: count=%d debris=%.0f attackers=%d level=%.1f status=%s",
             combat_count, total_debris, unique_attackers, level, status)
