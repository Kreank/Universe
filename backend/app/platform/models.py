"""SQLAlchemy-ORM-Modelle, exakt gemappt auf infra/db/init.sql.

Wichtig: Wir definieren KEINE Tabellen neu (kein create_all), wir spiegeln nur das
vorhandene Schema. PG-ENUM-Typen werden mit ``create_type=False`` referenziert, die
``embedding``-Spalte (pgvector) wird im Backend bewusst NICHT gemappt (gehoert dem
ai-worker)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base

# -- PG-ENUM-Typen (existieren bereits in der DB) -------------------------------
resource_type_enum = ENUM(
    "metal", "crystal", "deuterium", "energy",
    name="resource_type", create_type=False,
)
commander_status_enum = ENUM(
    "active", "training", "wounded", "captured", "dead",
    name="commander_status", create_type=False,
)
commander_rank_enum = ENUM(
    "cadet", "officer", "veteran", "elite", "legend",
    name="commander_rank", create_type=False,
)
specialization_enum = ENUM(
    "combat", "logistics", "spy", "research", "trade",
    name="specialization", create_type=False,
)
fleet_mission_enum = ENUM(
    "attack", "transport", "deploy", "hold", "colonize", "spy",
    "recycle", "expedition", "return", "mine", "trade",
    name="fleet_mission", create_type=False,
)
fleet_status_enum = ENUM(
    "flying", "arrived", "returning", "done",
    name="fleet_status", create_type=False,
)
occupant_type_enum = ENUM(
    "empty", "player", "npc", "debris",
    name="occupant_type", create_type=False,
)
transmission_type_enum = ENUM(
    "routine", "reaction", "demand", "combat_report", "big_moment", "system",
    "spy_report", "player_message",
    name="transmission_type", create_type=False,
)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    pw_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_active: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    score: Mapped[int] = mapped_column(BigInteger, default=0)
    is_protected: Mapped[bool] = mapped_column(Boolean, default=True)
    vacation_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    doctrine: Mapped[str | None] = mapped_column(Text, nullable=True)  # Imperiums-Doktrin (Doku 03b §9)
    doctrine_changed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # P2P-Handelsprofil (klassisch, unverbindlich): Spieler wirbt offen ein Tausch-Angebot,
    # ausgehandelt wird per Nachricht/Chat, abgewickelt mit normalen transport-Flotten.
    trade_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    trade_offer: Mapped[str | None] = mapped_column(Text, nullable=True)  # 'metal'|'crystal'|'deuterium'
    trade_want: Mapped[str | None] = mapped_column(Text, nullable=True)
    trade_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # Richtwert: want je 1 offer
    trade_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Planet(Base):
    __tablename__ = "planets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    system: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, default="Heimatplanet")
    planet_type: Mapped[str] = mapped_column(Text, default="normal")
    temp_max: Mapped[int] = mapped_column(Integer, default=40)
    fields_used: Mapped[int] = mapped_column(Integer, default=0)
    fields_max: Mapped[int] = mapped_column(Integer, default=163)
    is_homeworld: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Resource(Base):
    __tablename__ = "resources"

    planet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"), primary_key=True)
    type: Mapped[str] = mapped_column(resource_type_enum, primary_key=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    rate: Mapped[float] = mapped_column(Float, default=0.0)
    last_updated: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Building(Base):
    __tablename__ = "buildings"

    planet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"), primary_key=True)
    type: Mapped[str] = mapped_column(Text, primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    upgrade_finishes_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Research(Base):
    __tablename__ = "research"

    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    type: Mapped[str] = mapped_column(Text, primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    finishes_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Commander(Base):
    __tablename__ = "commanders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    persona: Mapped[dict] = mapped_column(JSONB, default=dict)
    traits: Mapped[list] = mapped_column(JSONB, default=list)
    specialization: Mapped[str] = mapped_column(specialization_enum, default="combat")
    rank: Mapped[str] = mapped_column(commander_rank_enum, default="cadet")
    grade: Mapped[str] = mapped_column(Text, default="C")  # Gueteklasse F..SSS (Doku 05a)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    morale: Mapped[int] = mapped_column(Integer, default=60)
    loyalty: Mapped[int] = mapped_column(Integer, default=100)
    # Unmut-Akkumulator (0..100): waechst je staerker der Kommandeur; Schwelle -> Forderung.
    unrest: Mapped[float] = mapped_column(Float, default=0.0)
    last_demand_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    span_capacity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(commander_status_enum, default="active")
    training_finishes_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CommanderLink(Base):
    __tablename__ = "commander_links"

    superior_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE"), primary_key=True)
    subordinate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE"), primary_key=True)


class Fleet(Base):
    __tablename__ = "fleets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    commander_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="SET NULL"), nullable=True)
    origin_planet_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="SET NULL"), nullable=True)
    target_galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    target_system: Mapped[int] = mapped_column(Integer, nullable=False)
    target_position: Mapped[int] = mapped_column(Integer, nullable=False)
    mission: Mapped[str] = mapped_column(fleet_mission_enum, nullable=False)
    status: Mapped[str] = mapped_column(fleet_status_enum, default="flying")
    depart_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    arrive_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    return_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cargo: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Auftrags-/Missionsdaten (z. B. Handel: {offer_res, offer_amount, want_res}).
    mission_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Ship(Base):
    __tablename__ = "ships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planet_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"), nullable=True)
    fleet_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        CheckConstraint("count >= 0", name="ships_count_check"),
    )


class Defense(Base):
    __tablename__ = "defenses"

    planet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"), primary_key=True)
    type: Mapped[str] = mapped_column(Text, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class ShipyardQueueItem(Base):
    __tablename__ = "shipyard_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)  # 'ship' | 'defense'
    finishes_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        CheckConstraint("count > 0", name="shipyard_queue_count_check"),
    )


class ReactionBank(Base):
    __tablename__ = "reaction_banks"
    # Hinweis: Spalte ``embedding`` (vector(768)) wird bewusst NICHT gemappt.

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commander_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE"))
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Transmission(Base):
    __tablename__ = "transmissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    # Absender bei Spieler-zu-Spieler-Nachrichten (type 'player_message'); NULL = System.
    from_player_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    commander_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(transmission_type_enum, default="routine")
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    requires_decision: Mapped[bool] = mapped_column(Boolean, default=False)
    decision_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CombatReport(Base):
    __tablename__ = "combat_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attacker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    defender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    outcome: Mapped[dict] = mapped_column(JSONB, nullable=False)
    loot: Mapped[dict] = mapped_column(JSONB, default=dict)
    debris: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UniverseCell(Base):
    __tablename__ = "universe_cells"

    galaxy: Mapped[int] = mapped_column(Integer, primary_key=True)
    system: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    occupant_type: Mapped[str] = mapped_column(occupant_type_enum, default="empty")
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Truemmerfeld am Ort (nach Kaempfen), {metal, crystal}; vom Recycler einsammelbar.
    debris_field: Mapped[dict] = mapped_column(JSONB, default=dict)


class NpcEmpire(Base):
    __tablename__ = "npc_empires"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    behavior_profile: Mapped[str] = mapped_column(Text, default="defensive")
    galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    system: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    fleet: Mapped[dict] = mapped_column(JSONB, default=dict)
    defenses: Mapped[dict] = mapped_column(JSONB, default=dict)
    resources: Mapped[dict] = mapped_column(JSONB, default=dict)
    baseline: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Haendler-Markt (nur fuer behavior_profile=='merchant'): {spec, stock:{metal,crystal,deuterium}}.
    market: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_action_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attack_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class StationedFleet(Base):
    """Eine an einem System stationierte Patrouillen-/Eskortflotte (deploy-Mission).

    Schiffe sind hier gebunden (nicht in Planet-Garnison/Fleet -> fuer den Besitzer
    gesperrt), bis er sie zurueckruft. Kann ein Eskort-Angebot tragen (Radius + Gebuehr)
    und ist ein gueltiges Angriffsziel (wird sie zerstoert, erlischt das Angebot)."""
    __tablename__ = "stationed_fleets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    home_planet_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="SET NULL"), nullable=True)
    galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    system: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    ships: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Eskort-Angebot (optional): deckt Routen im Umkreis escort_radius, Gebuehr = % Frachtwert.
    escort_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    escort_radius: Mapped[int] = mapped_column(Integer, default=0)
    escort_fee_pct: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class WorldMarket(Base):
    """Singleton (id=1) fuer den globalen Handelsindex.

    Haelt den EMA-geglaetteten liquiden Weltvorrat je Ressource (Summe ueber alle
    Spieler-Planeten) + die zugrunde gelegte aktive Spielerzahl. Der Kurs der
    Handelszentren (behavior_profile 'trade_center') wird hieraus abgeleitet
    (siehe app.fleet.trade_index). Vom Index-Tick periodisch aktualisiert."""
    __tablename__ = "world_market"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    supply: Mapped[dict] = mapped_column(JSONB, default=dict)
    players: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NpcAttack(Base):
    """Eine eingehende NPC-Angriffsflotte auf einen Spieler-Planeten (im Anflug).

    Isoliert vom Spieler-Flotten-System (Fleet) — NPCs besitzen keine Fleet-Zeilen.
    Bei Ankunft (arrive_at) loest ein Scheduler-Job ``resolve_npc_attack`` den Kampf auf."""
    __tablename__ = "npc_attacks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("npc_empires.id", ondelete="CASCADE"))
    target_player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    target_planet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"))
    target_galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    target_system: Mapped[int] = mapped_column(Integer, nullable=False)
    target_position: Mapped[int] = mapped_column(Integer, nullable=False)
    fleet: Mapped[dict] = mapped_column(JSONB, default=dict)  # {type: count} der Angreifer
    status: Mapped[str] = mapped_column(Text, default="incoming")  # 'incoming' | 'resolved'
    arrive_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PlayerDiscovery(Base):
    __tablename__ = "player_discoveries"

    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    galaxy: Mapped[int] = mapped_column(Integer, primary_key=True)
    system: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    intel: Mapped[dict] = mapped_column(JSONB, default=dict)
    level: Mapped[int] = mapped_column(Integer, default=1)
    discovered_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TradeReputation(Base):
    """Handelsreputation eines Spielers bei einem Haendler-NPC.

    ``volume`` ist das kumulierte Handelsvolumen (Marktwert der bisher angebotenen
    Ware); daraus leitet sich die Reputationsstufe ab (volume // volume_per_level,
    gedeckelt auf max_level), die die Haendler-Marge fuer Stammkunden senkt.
    Composite-PK (player_id, npc_id) — Vorbild: PlayerDiscovery."""
    __tablename__ = "trade_reputation"

    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    npc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("npc_empires.id", ondelete="CASCADE"), primary_key=True)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
