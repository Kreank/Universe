"""Allianz-Verwaltung: Gruendung, Mitglieder/Rollen, Einladungen, Pool.

Allianzen sind die kooperative Ebene OBEN AUF der individuellen Spieler-Forschung. Mitgliedschaft
ist exklusiv (ein Spieler in hoechstens einer Allianz; ``alliance_members.player_id`` = PK +
denormalisiert ``Player.alliance_id`` fuer schnellen Resolver-Zugriff). Pool-Einzahlungen sind
race-sicher (Row-Lock auf die Allianz-Zeile, Muster wie ``book_slot``).
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import spend_resources
from app.platform.balance import get_balance
from app.platform.models import (
    Alliance,
    AllianceInvite,
    AllianceMember,
    AllianceStation,
    Planet,
    Player,
)

ROLES = ("member", "officer", "founder")
RES_KEYS = ("metal", "crystal", "deuterium")


def _acfg() -> dict:
    return get_balance().data.get("alliance", {})


def _role_rank(role: str) -> int:
    return ROLES.index(role) if role in ROLES else 0


async def get_membership(session: AsyncSession, player_id: uuid.UUID) -> AllianceMember | None:
    return await session.get(AllianceMember, player_id)


async def _members(session: AsyncSession, alliance_id: uuid.UUID) -> list[AllianceMember]:
    return list((await session.execute(
        select(AllianceMember).where(AllianceMember.alliance_id == alliance_id)
        .order_by(AllianceMember.joined_at)
    )).scalars().all())


async def _member_count(session: AsyncSession, alliance_id: uuid.UUID) -> int:
    return int((await session.execute(
        select(func.count()).select_from(AllianceMember).where(AllianceMember.alliance_id == alliance_id)
    )).scalar_one())


async def notify_alliance(
    session: AsyncSession, alliance_id: uuid.UUID, subject: str, body: str, ttype: str = "system"
) -> None:
    """Sendet eine System-Nachricht an ALLE Mitglieder der Allianz (z. B. Stations-Zerstoerung)."""
    from app.messaging.service import create_system_transmission
    for mem in await _members(session, alliance_id):
        await create_system_transmission(
            session, player_id=mem.player_id, subject=subject, body=body, ttype=ttype,
        )


async def _require_role(session: AsyncSession, player: Player, min_role: str) -> AllianceMember:
    m = await get_membership(session, player.id)
    if m is None:
        raise ValueError("Du bist in keiner Allianz.")
    if _role_rank(m.role) < _role_rank(min_role):
        raise PermissionError("Dafuer fehlt dir die Berechtigung.")
    return m


# -- Gruendung / Aufloesung -----------------------------------------------------

async def create_alliance(session: AsyncSession, player: Player, name: str, tag: str) -> Alliance:
    if await get_membership(session, player.id) is not None:
        raise ValueError("Du bist bereits in einer Allianz.")
    name = (name or "").strip()
    tag = (tag or "").strip()
    if not (3 <= len(name) <= 40):
        raise ValueError("Name muss 3–40 Zeichen lang sein.")
    if not (2 <= len(tag) <= 6):
        raise ValueError("Tag muss 2–6 Zeichen lang sein.")
    clash = (await session.execute(
        select(Alliance).where(
            (func.lower(Alliance.name) == name.lower()) | (func.lower(Alliance.tag) == tag.lower())
        )
    )).scalars().first()
    if clash is not None:
        raise ValueError("Name oder Tag ist bereits vergeben.")
    home = (await session.execute(
        select(Planet).where(Planet.player_id == player.id)
        .order_by(Planet.is_homeworld.desc(), Planet.created_at)
    )).scalars().first()
    if home is None:
        raise ValueError("Kein Planet gefunden.")
    cost = _acfg().get("create_cost", {})
    if not await spend_resources(session, home, dict(cost)):
        need = " / ".join(f"{int(cost.get(k, 0)):,}".replace(",", ".") + " " + lbl
                          for k, lbl in (("metal", "Metall"), ("crystal", "Kristall"),
                                         ("deuterium", "Deuterium")) if cost.get(k, 0))
        raise ValueError(f"Nicht genug Ressourcen auf dem Heimatplaneten. Gruendung kostet: {need}.")
    alliance = Alliance(name=name, tag=tag, founder_id=player.id, pool={}, research_levels={})
    session.add(alliance)
    await session.flush()
    session.add(AllianceMember(player_id=player.id, alliance_id=alliance.id, role="founder"))
    player.alliance_id = alliance.id
    return alliance


async def disband(session: AsyncSession, player: Player) -> None:
    m = await _require_role(session, player, "founder")
    alliance_id = m.alliance_id
    for mem in await _members(session, alliance_id):
        p = await session.get(Player, mem.player_id)
        if p is not None:
            p.alliance_id = None
    al = await session.get(Alliance, alliance_id)
    if al is not None:
        await session.delete(al)  # CASCADE: members, stations, invites


# -- Einladungen / Beitritt / Austritt ------------------------------------------

async def invite(session: AsyncSession, player: Player, target_player_id: uuid.UUID) -> None:
    m = await _require_role(session, player, "officer")
    target = await session.get(Player, target_player_id)
    if target is None:
        raise ValueError("Spieler nicht gefunden.")
    if await get_membership(session, target.id) is not None:
        raise ValueError("Spieler ist bereits in einer Allianz.")
    if await _member_count(session, m.alliance_id) >= int(_acfg().get("max_members", 50)):
        raise ValueError("Die Allianz ist voll.")
    if await session.get(AllianceInvite, (m.alliance_id, target.id)) is None:
        session.add(AllianceInvite(alliance_id=m.alliance_id, player_id=target.id, invited_by=player.id))


async def accept_invite(session: AsyncSession, player: Player, alliance_id: uuid.UUID) -> Alliance:
    if await get_membership(session, player.id) is not None:
        raise ValueError("Du bist bereits in einer Allianz.")
    inv = await session.get(AllianceInvite, (alliance_id, player.id))
    if inv is None:
        raise ValueError("Keine Einladung dieser Allianz vorhanden.")
    if await _member_count(session, alliance_id) >= int(_acfg().get("max_members", 50)):
        raise ValueError("Die Allianz ist voll.")
    al = await session.get(Alliance, alliance_id)
    if al is None:
        raise ValueError("Allianz nicht gefunden.")
    session.add(AllianceMember(player_id=player.id, alliance_id=alliance_id, role="member"))
    player.alliance_id = alliance_id
    # Alle (auch andere) Einladungen dieses Spielers entfernen.
    await session.execute(delete(AllianceInvite).where(AllianceInvite.player_id == player.id))
    return al


async def decline_invite(session: AsyncSession, player: Player, alliance_id: uuid.UUID) -> None:
    inv = await session.get(AllianceInvite, (alliance_id, player.id))
    if inv is not None:
        await session.delete(inv)


async def list_invites_for(session: AsyncSession, player_id: uuid.UUID) -> list[Alliance]:
    rows = (await session.execute(
        select(Alliance).join(AllianceInvite, AllianceInvite.alliance_id == Alliance.id)
        .where(AllianceInvite.player_id == player_id)
    )).scalars().all()
    return list(rows)


async def leave(session: AsyncSession, player: Player) -> None:
    m = await get_membership(session, player.id)
    if m is None:
        raise ValueError("Du bist in keiner Allianz.")
    if m.role == "founder":
        raise ValueError("Gruender koennen nicht austreten — Allianz aufloesen oder Fuehrung uebergeben.")
    await session.delete(m)
    player.alliance_id = None


async def kick(session: AsyncSession, player: Player, target_player_id: uuid.UUID) -> None:
    m = await _require_role(session, player, "officer")
    target_m = await get_membership(session, target_player_id)
    if target_m is None or target_m.alliance_id != m.alliance_id:
        raise ValueError("Mitglied nicht gefunden.")
    if _role_rank(target_m.role) >= _role_rank(m.role):
        raise PermissionError("Du kannst niemanden mit gleichem oder hoeherem Rang entfernen.")
    p = await session.get(Player, target_player_id)
    if p is not None:
        p.alliance_id = None
    await session.delete(target_m)


async def set_role(session: AsyncSession, player: Player, target_player_id: uuid.UUID, role: str) -> None:
    m = await _require_role(session, player, "founder")
    if role not in ("member", "officer"):
        raise ValueError("Rolle muss 'member' oder 'officer' sein.")
    target_m = await get_membership(session, target_player_id)
    if target_m is None or target_m.alliance_id != m.alliance_id:
        raise ValueError("Mitglied nicht gefunden.")
    if target_m.player_id == player.id:
        raise ValueError("Die eigene Rolle kann hier nicht geaendert werden.")
    target_m.role = role


async def transfer_leadership(session: AsyncSession, player: Player, target_player_id: uuid.UUID) -> None:
    m = await _require_role(session, player, "founder")
    target_m = await get_membership(session, target_player_id)
    if target_m is None or target_m.alliance_id != m.alliance_id:
        raise ValueError("Mitglied nicht gefunden.")
    target_m.role = "founder"
    m.role = "officer"
    al = await session.get(Alliance, m.alliance_id)
    if al is not None:
        al.founder_id = target_player_id


# -- Pool -----------------------------------------------------------------------

async def deposit(session: AsyncSession, player: Player, planet_id: uuid.UUID, resources: dict) -> dict:
    m = await get_membership(session, player.id)
    if m is None:
        raise ValueError("Du bist in keiner Allianz.")
    planet = await session.get(Planet, planet_id)
    if planet is None or planet.player_id != player.id:
        raise ValueError("Planet nicht gefunden.")
    amounts = {k: float(resources.get(k, 0) or 0) for k in RES_KEYS if float(resources.get(k, 0) or 0) > 0}
    if not amounts:
        raise ValueError("Nichts zum Einzahlen angegeben.")
    if not await spend_resources(session, planet, amounts):
        raise ValueError("Nicht genug Ressourcen auf dem Planeten.")
    # Race-sicher: Allianz-Zeile sperren, Pool addieren.
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()
    pool = dict(al.pool or {})
    for k, v in amounts.items():
        pool[k] = round(float(pool.get(k, 0)) + v, 2)
    al.pool = pool
    return pool


# -- Serialisierung -------------------------------------------------------------

async def overview(session: AsyncSession, alliance: Alliance) -> dict:
    members = await _members(session, alliance.id)
    out_members = []
    for mem in members:
        p = await session.get(Player, mem.player_id)
        out_members.append({
            "player_id": str(mem.player_id),
            "name": p.display_name if p else "Unbekannt",
            "role": mem.role,
            "joined_at": mem.joined_at.isoformat() if mem.joined_at else None,
        })
    stations = (await session.execute(
        select(AllianceStation).where(AllianceStation.alliance_id == alliance.id)
    )).scalars().all()
    return {
        "id": str(alliance.id),
        "name": alliance.name,
        "tag": alliance.tag,
        "founder_id": str(alliance.founder_id) if alliance.founder_id else None,
        "pool": alliance.pool or {},
        "research_levels": alliance.research_levels or {},
        "members": out_members,
        "member_count": len(out_members),
        "max_members": int(_acfg().get("max_members", 50)),
        "stations": [
            {
                "id": str(s.id),
                "coords": f"{s.galaxy}:{s.system}:{s.position}",
                "galaxy": s.galaxy, "system": s.system, "position": s.position,
                "radius_level": s.research_radius_level,
                "fuel": s.fuel, "hp": s.hp, "status": s.status,
            }
            for s in stations
        ],
    }
