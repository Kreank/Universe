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
    "metal", "crystal", "deuterium", "energy", "antimatter", "dark_matter",
    name="resource_type", create_type=False,
)
commander_status_enum = ENUM(
    "active", "training", "wounded", "captured", "dead", "defected", "mutinous",
    name="commander_status", create_type=False,
)
commander_rank_enum = ENUM(
    "cadet", "officer", "veteran", "elite", "legend",
    name="commander_rank", create_type=False,
)
specialization_enum = ENUM(
    "combat", "logistics", "spy", "research", "trade", "admin",
    name="specialization", create_type=False,
)
fleet_mission_enum = ENUM(
    "attack", "transport", "deploy", "hold", "colonize", "spy",
    "recycle", "expedition", "return", "mine", "trade", "intercept", "escort",
    name="fleet_mission", create_type=False,
)
fleet_status_enum = ENUM(
    "flying", "arrived", "returning", "done",
    name="fleet_status", create_type=False,
)
occupant_type_enum = ENUM(
    "empty", "player", "npc", "debris", "asteroid_field",
    name="occupant_type", create_type=False,
)
transmission_type_enum = ENUM(
    "routine", "reaction", "demand", "combat_report", "big_moment", "system",
    "spy_report", "player_message", "npc_diplomacy",
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
    # Exotische Endgame-Ressourcen (kontoweit, erspielt — NIE kaufbar, kein P2W). Dunkle
    # Materie = zivil/Forschung, Antimaterie = militaerisch/Energie. Erbeutet auf Expeditionen.
    dark_matter: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    antimatter: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    # P2P-Handelsprofil (klassisch, unverbindlich): Spieler wirbt offen ein Tausch-Angebot,
    # ausgehandelt wird per Nachricht/Chat, abgewickelt mit normalen transport-Flotten.
    trade_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    trade_offer: Mapped[str | None] = mapped_column(Text, nullable=True)  # 'metal'|'crystal'|'deuterium'
    trade_want: Mapped[str | None] = mapped_column(Text, nullable=True)
    trade_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # Richtwert: want je 1 offer
    trade_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Allianz-Zugehoerigkeit (denormalisiert, synchron mit alliance_members) — Schnell-Zugriff
    # fuer den Bonus-Resolver. NULL = solo.
    alliance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alliances.id", ondelete="SET NULL"), nullable=True
    )


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
    # Gouverneur (Kommandeur) dieses Planeten -> Produktions-Bonus (economy_bonus).
    governor_commander_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="SET NULL"), nullable=True)
    # Mond: planet_type='moon' + parent_planet_id (gebunden an den Planeten, gleiche Koordinate).
    parent_planet_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"), nullable=True)
    last_jump_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class Megastructure(Base):
    """Endgame-Megastruktur (kontoweit, stufenweiser Bau). Eine Zeile je (Spieler, Typ).

    ``building_until`` != NULL => die naechste Stufe ist gerade im Bau (Echtzeit-Timer).
    Es darf nur EIN Megastruktur-Projekt je Spieler gleichzeitig laufen (Anti-Snowball)."""
    __tablename__ = "megastructures"

    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    type: Mapped[str] = mapped_column(Text, primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    building_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    last_ability_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # RPG-Entwicklung: Skillpunkte (bei Rang-Up), erlernte Faehigkeiten [{key,level}],
    # Cooldown-Zeitstempel je Faehigkeit {key: iso}.
    skill_points: Mapped[int] = mapped_column(Integer, default=1)
    abilities: Mapped[list] = mapped_column(JSONB, default=list)
    ability_cooldowns: Mapped[dict] = mapped_column(JSONB, default=dict)
    span_capacity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(commander_status_enum, default="active")
    training_finishes_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Welle 2 (Gedaechtnis & Eigenleben): Anker fuer den Meuterei-Cooldown + letzten Memory-Digest.
    last_mutiny_check_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_digest_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CommanderMemory(Base):
    """Eine Erinnerung eines Kommandeurs (Welle 2): Schlacht/Expedition/Forderung/Verlust.

    ``context`` traegt die Details ({enemy_name, planet, outcome, value, about_player_id,
    about_npc_id ...}), ``sentiment`` (positive|negative|neutral) faerbt das vom ai-worker
    (memory_digest) verdichtete Erinnerungs-Narrativ — und damit die kuenftigen Funksprueche."""
    __tablename__ = "commander_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commander_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE")
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    sentiment: Mapped[str] = mapped_column(Text, default="neutral")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CommanderRelationship(Base):
    """Beziehung zwischen ZWEI Kommandeuren desselben Spielers (Welle 2).

    PK (a, b) mit der Konvention ``a < b`` (lexikografisch nach UUID-String) -> jede Paarung
    existiert genau einmal. ``rel_type`` = rivalry | respect | grudge | bond, ``strength`` 0..1."""
    __tablename__ = "commander_relationships"

    commander_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE"), primary_key=True
    )
    commander_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE"), primary_key=True
    )
    rel_type: Mapped[str] = mapped_column(Text, nullable=False)
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    last_interaction: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)


class CommanderOpinion(Base):
    """Meinung eines Kommandeurs ueber einen Gegner (Welle 2): genau EINES von about_player_id /
    about_npc_id ist gesetzt. Eindeutigkeit pro (commander, ziel) ueber partielle Unique-Indizes.
    ``opinion_type`` = respects | despises | fears | envies, ``strength`` 0..1."""
    __tablename__ = "commander_opinions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commander_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE")
    )
    about_player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=True
    )
    about_npc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("npc_empires.id", ondelete="CASCADE"), nullable=True
    )
    opinion_type: Mapped[str] = mapped_column(Text, nullable=False)
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    last_reinforced_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CommanderGrievance(Base):
    """Aufgestaute Kraenkung eines Kommandeurs (Welle 2) -> Meuterei-Treiber.

    ``grievance_type`` = ignored_demand | risky_missions | denied_promotion | combat_neglect.
    Wiederholte Vorfaelle erhoehen ``severity`` + ``accumulated_count``; ``resolved_at`` != NULL
    nimmt die Kraenkung aus der Meuterei-Summe (beigelegt)."""
    __tablename__ = "commander_grievances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commander_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE")
    )
    grievance_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, default=0)
    accumulated_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommanderLink(Base):
    __tablename__ = "commander_links"

    superior_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE"), primary_key=True)
    subordinate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE"), primary_key=True)


class CommanderItem(Base):
    """Ausruestungs-Item im Spieler-Inventar. Genau ein Item je Slot/Kommandeur,
    wenn ``equipped_commander_id`` gesetzt ist; sonst frei im Inventar."""
    __tablename__ = "commander_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    item_key: Mapped[str] = mapped_column(Text, nullable=False)
    slot: Mapped[str] = mapped_column(Text, nullable=False)  # head | hands | chest | shoes
    rarity: Mapped[str] = mapped_column(Text, default="common")  # common | rare | epic
    equipped_commander_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="SET NULL"), nullable=True
    )
    acquired_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


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
    # ``finishes_at`` = Fertigstellung der NAECHSTEN Einheit; ``seconds_each`` = Dauer je Einheit
    # (stueckweise Fertigstellung). Legacy-Zeilen: seconds_each=0 -> atomar wie frueher.
    finishes_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    seconds_each: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        CheckConstraint("count > 0", name="shipyard_queue_count_check"),
    )


class ReactionBank(Base):
    __tablename__ = "reaction_banks"
    # Hinweis: Spalte ``embedding`` (vector(768)) wird bewusst NICHT gemappt.

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Genau EINES von commander_id/npc_id ist gesetzt (Persona-Quelle: Spieler-Commander ODER NPC-Imperium).
    commander_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commanders.id", ondelete="CASCADE"), nullable=True
    )
    npc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("npc_empires.id", ondelete="CASCADE"), nullable=True
    )
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


class AsteroidField(Base):
    """Endliches, regenerierendes Erz-Vorkommen (occupant 'asteroid_field' der Zelle).
    Bergbauschiffe (mine-Mission) foerdern hier; Reichtum (mult) skaliert Vorrat + Ertrag."""
    __tablename__ = "asteroid_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    system: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    richness: Mapped[str] = mapped_column(Text, default="normal")  # Tier-Name
    mult: Mapped[float] = mapped_column(Float, default=1.0)        # Reichtums-Multiplikator
    metal_remaining: Mapped[float] = mapped_column(Float, default=0.0)
    crystal_remaining: Mapped[float] = mapped_column(Float, default=0.0)
    metal_max: Mapped[float] = mapped_column(Float, default=0.0)
    crystal_max: Mapped[float] = mapped_column(Float, default=0.0)
    last_regen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Ablaufzeit (gestaffelt 24-48h): danach wandert das Feld (despawn + neu woanders),
    # damit Hot-Spotting vermieden wird. NULL = unbegrenzt (Alt-Felder bis zum Backfill).
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FarmRoute(Base):
    """Farm-Routine: dauerhaft fliegende Sammelschleife einer Flotte ueber Asteroiden-/
    Truemmerfelder. Persistente Definition + zugeordnete Schiffe; der Controller
    (``fleet/routines.py``) startet je Zyklus einen getaggten mine/recycle-Flug zum
    aktuellen Waypoint (``cursor``) und advanced den Cursor bei Rueckkehr."""
    __tablename__ = "farm_routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    home_planet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # {typ: count} der zugeordneten Farm-Flotte.
    ships: Mapped[dict] = mapped_column(JSONB, default=dict)
    # [{galaxy, system, position}] in Flugreihenfolge.
    waypoints: Mapped[list] = mapped_column(JSONB, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(Text, default="idle")          # idle | flying | paused
    pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    active_fleet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Alliance(Base):
    """Allianz: kooperative Ebene mit gemeinsamem Ressourcen-Pool + Allianz-Forschung
    (research_levels: {"<tree>.<node>": level}). Mitglieder in ``alliance_members``."""
    __tablename__ = "alliances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    tag: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    founder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    pool: Mapped[dict] = mapped_column(JSONB, default=dict)                 # {metal, crystal, deuterium}
    research_levels: Mapped[dict] = mapped_column(JSONB, default=dict)      # {"<tree>.<node>": level}
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AllianceMember(Base):
    """Mitgliedschaft (genau eine je Spieler -> player_id ist PK). Rolle: founder|officer|member."""
    __tablename__ = "alliance_members"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    alliance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alliances.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, default="member")
    joined_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AllianceStation(Base):
    """Allianz-Station: physischer Anker, projiziert die Baum-Spezialisierung in eine
    Einflusszone (Radius = base + research_radius_level, Cap aus balance). Upkeep zehrt fuel;
    leer -> status 'inactive'. Zerstoerbar (braucht >=2 Angreifer)."""
    __tablename__ = "alliance_stations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alliance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alliances.id", ondelete="CASCADE"), nullable=False
    )
    galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    system: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    research_radius_level: Mapped[int] = mapped_column(Integer, default=0)
    # Verteidigungs-Tech der Station (eigene „Stations-Forschung"): startet bei 1, aufwertbar bis
    # max_tech (12). Hebt Angriff/Schild/Huelle der Abwehrbatterien (Abfang + Belagerung).
    defense_tech_level: Mapped[int] = mapped_column(Integer, default=1)
    fuel: Mapped[float] = mapped_column(Float, default=0.0)
    hp: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(Text, default="active")  # active | inactive | transit | destroyed
    built_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_upkeep_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Belagerungs-Status (Phase 2): {"attackers": {player_id: {"damage": float, "at": iso}}, "last_attack_at": iso}.
    siege: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Transit-Status (Umstationieren, 2026-06-17): waehrend status='transit' gesetzt. Enthaelt
    # {origin:[g,s,p], target:[g,s,p], depart_at, arrive_at, returning:bool, escort:{type:count},
    # escort_planet_id, escort_owner_id, deuterium}. Leer {} wenn die Station ortsfest ist.
    transit: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Montierte Stations-Module (Slots, 2026-06-17): {module_type: count}, Summe <= Slot-Zahl.
    # Heben Kampfwerte/HP/Transit-Tempo.
    modules: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Slot-Ausbaustufe (eigener Pfad, getrennt vom Radius): Slots = base_slots + slot_level.
    slot_level: Mapped[int] = mapped_column(Integer, default=0)


class AllianceInvite(Base):
    """Offene Einladung in eine Allianz (officer+ lädt ein, Spieler nimmt an)."""
    __tablename__ = "alliance_invites"

    alliance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alliances.id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


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
    # KI-Persona (background/voice) — vom ai-worker per persona_init angereichert (Funksprueche).
    persona: Mapped[dict] = mapped_column(JSONB, default=dict)
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
    # Treibstoff-Vorrat: NULL = eigenes Gebiet (gratis), Zahl = mitgefuehrter Deuterium-Vorrat
    # vorgeschobener Stationierung (zehrt per Tick, leer -> Zwangs-Rueckkehr).
    fuel: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Mitgefuehrte Nicht-Treibstoff-Fracht (Metall/Kristall/Exoten), die auf einer vorgeschobenen
    # Station an Bord bleibt und beim Rueckruf zurueckkommt — sonst ginge sie verloren.
    cargo: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # Eskort-Angebot (optional): deckt Routen im Umkreis escort_radius, Gebuehr = % Frachtwert.
    escort_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    escort_radius: Mapped[int] = mapped_column(Integer, default=0)
    escort_fee_pct: Mapped[float] = mapped_column(Float, default=0.0)
    # Abfang-Modus (A): faengt feindliche Flotten ab, deren galaxie-interne Route das
    # Stations-System (+/- intercept_radius) kreuzt (balance.combat.interception).
    intercept_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    intercept_radius: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EscortJob(Base):
    """Eskort-Gesuch (Nachfrage-Seite des Geleitschutz-Marktes): ein Trader POSTET aktiv
    einen Auftrag (Route + geschaetzter Frachtwert + max. Gebuehr), Eskort-Anbieter nehmen ihn
    mit einer ihrer Eskort-Stationen (``StationedFleet``, escort_enabled) an.

    Spiegelt das bestehende Angebots-Modell (escort_covers/charge_trade_escorts): die Route ist
    galaxie-intern (origin_system -> target_system), eine Station deckt sie, wenn ihr System im
    Intervall +/- escort_radius liegt. Lebenszyklus ueber ``status``; abgelaufene Gesuche
    (``expires_at``) werden beim Listen lazy auf 'expired' gesetzt. Nach der Annahme ist die
    angenommene Station ein normales Eskort-Angebot auf der Route -> der Trader bucht sie beim
    Handel ueber den bestehenden escort_ids/charge_trade_escorts-Pfad (kein doppeltes Abrechnen)."""
    __tablename__ = "escort_job"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    origin_galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_system: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_position: Mapped[int] = mapped_column(Integer, nullable=False)
    target_galaxy: Mapped[int] = mapped_column(Integer, nullable=False)
    target_system: Mapped[int] = mapped_column(Integer, nullable=False)
    target_position: Mapped[int] = mapped_column(Integer, nullable=False)
    # Geschaetzter Frachtwert der Route (Basis fuer die Gebuehr = fee_pct * cargo_value).
    cargo_value: Mapped[float] = mapped_column(Float, default=0.0)
    # Hoechste Gebuehr (% Frachtwert), die der Trader zu zahlen bereit ist.
    max_fee_pct: Mapped[float] = mapped_column(Float, default=0.0)
    # Mindest-Kampfkraft der Eskorte, die der Trader verlangt (0 = egal).
    min_power: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    # 'open' | 'accepted' | 'cancelled' | 'expired' | 'done'.
    status: Mapped[str] = mapped_column(Text, default="open", server_default="open")
    accepted_station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stationed_fleets.id", ondelete="SET NULL"), nullable=True
    )
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    accepted_fee_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
    # Optionale Sonder-Flags (z. B. nach Piraten-Bestechung): {debris_mult, item_chance}.
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
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


class TradeLog(Base):
    """Handelshistorie: eine Zeile je abgeschlossenem Handel eines Spielers.

    ``partner_kind`` = 'npc' (Haendler/Handelszentrum) oder 'player' (P2P-Hub, Folge-Schritt C).
    ``partner_id`` ist NICHT als FK gebunden (der Partner — NPC oder Spieler — soll auch nach
    seiner Loeschung in der Historie lesbar bleiben); ``partner_name`` haelt den Klartext.
    Geschrieben best-effort aus ``resolve_trade`` (darf den Handel nie stoeren)."""
    __tablename__ = "trade_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    partner_kind: Mapped[str] = mapped_column(Text, default="npc")  # npc | player
    partner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    partner_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    offered_res: Mapped[str] = mapped_column(Text, nullable=False)
    offered_amount: Mapped[float] = mapped_column(Float, default=0.0)
    received_res: Mapped[str] = mapped_column(Text, nullable=False)
    received_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NpcRelation(Base):
    """Beziehung Spieler<->NPC-Imperium (Welle 1: verhandelbare KI-Imperien).

    Eine Zeile je (Spieler, NPC). ``status`` steuert das NPC-Verhalten:
    ``allied``/``ceasefire`` (mit ``ceasefire_until`` > now) schuetzen den Spieler vor
    NPC-Angriffen; ``hostile``/``broken_pact`` markieren gebrochene Pakte. Tribut +
    Verrats-Flags + pos/neg Aktionen bilden die HISTORIE, die die KI-Entscheidung
    (ai-worker ``npc_decision``) charaktertreu faerbt. Composite-PK — Vorbild: TradeReputation."""
    __tablename__ = "npc_relations"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    npc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("npc_empires.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(Text, default="neutral")  # neutral|allied|ceasefire|hostile|broken_pact
    alliance_since: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ceasefire_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tribute_metal_per_cycle: Mapped[float] = mapped_column(Float, default=0.0)
    tribute_last_paid: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    betrayed_by_player: Mapped[bool] = mapped_column(Boolean, default=False)
    betrayed_by_npc: Mapped[bool] = mapped_column(Boolean, default=False)
    broken_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_actions: Mapped[int] = mapped_column(Integer, default=0)
    negative_actions: Mapped[int] = mapped_column(Integer, default=0)
    last_decision_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NpcDecision(Base):
    """Audit einer KI-Verhandlungs-Entscheidung (Nachvollziehbarkeit + Chronik-Quelle, W3).

    Haelt das vom Spieler angebotene (bereits geklemmte) Angebot, die LLM-Wahl
    (accept|reject|counter) samt Begruendung und die tatsaechlich angewandten Konditionen."""
    __tablename__ = "npc_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("npc_empires.id", ondelete="CASCADE"))
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    offer_type: Mapped[str] = mapped_column(Text, nullable=False)  # alliance|ceasefire|tribute
    offered_terms: Mapped[dict] = mapped_column(JSONB, default=dict)
    npc_choice: Mapped[str | None] = mapped_column(Text, nullable=True)  # accept|reject|counter
    npc_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_result: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PlayerReputation(Base):
    """Globaler Verrats-Ruf eines Spielers (W1 gesetzt, in W3/Chronik wiederverwendet).

    ``betrayals`` = gebrochene Pakte (sinkt das Vertrauen aller NPCs), ``alliances_honored``
    = gehaltene Buendnisse. Bewusst schlank (eine Zeile je Spieler)."""
    __tablename__ = "player_reputation"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    betrayals: Mapped[int] = mapped_column(Integer, default=0)
    alliances_honored: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GameChronicle(Base):
    """Ein Eintrag der „Lebenden Galaxie-Chronik" (Welle 3): ein vom ai-worker (Erzaehler
    'historian') geschriebener, epischer aber FAKTENTREUER Saga-Eintrag ueber die echten
    Spieler-Taten eines Zeitfensters.

    ``key_events`` haelt ein Objekt ``{"events": [...], "snapshot": {...}}``: die
    erzaehlwuerdigen Fakten (Schlachten/Auf-Abstiege/Verrat/Welt-Events) UND den Score-/Ruf-
    Snapshot des Fensters, damit die naechste Chronik die Veraenderung erkennt (kein extra
    Snapshot-Tabellen-Zoo). ``status`` = pending (Backend legt an) -> published (ai-worker
    schreibt title+body + published_at)."""
    __tablename__ = "game_chronicle"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, default="", server_default="")
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    narrator: Mapped[str] = mapped_column(Text, default="historian", server_default="historian")
    span_start: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    span_end: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    key_events: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="[]")
    status: Mapped[str] = mapped_column(Text, default="pending", server_default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Feedback(Base):
    """Spieler-Feedback aus der Testphase (Bug-Report / Idee / Sonstiges).

    Bewusst entkoppelt von der Spiel-Logik: nur Sammelbecken fuers Entwickler-Postfach.
    ``player_id`` ist nullable (ON DELETE SET NULL), damit Meldungen einen geloeschten
    Test-Account ueberleben; ``display_name`` haelt den Namen zum Zeitpunkt der Meldung."""
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)  # 'bug' | 'idea' | 'other'
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[str | None] = mapped_column(Text, nullable=True)        # Route, auf der gemeldet wurde
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)  # Browser/Geraet (gekuerzt)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CosmicEvent(Base):
    """Dynamisches Welt-/Karten-Event mit Lebensdauer (Komet, Anomalie, Schwarzmarkt, Wrack,
    Utopia-Werft, Sonnensturm, Flüchtlinge, Schwarzes Loch ...) ODER ein persönliches Event
    (Piraten-Razzia, Minen-Streik) als Tracking-Eintrag.

    Karten-Events liegen als OVERLAY auf einer Galaxie-Koordinate (blockieren die Zelle NICHT,
    Vorbild: AsteroidField). ``data`` traegt event-spezifische Felder (Vorrat, Belohnung, Beitraege,
    Drohnen ...). ``status`` = active | resolved | expired."""
    __tablename__ = "cosmic_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)        # 'wandering_comet' | ...
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="global")  # global|system|personal
    galaxy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    system: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=True
    )
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    spawned_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AggressionHistory(Base):
    """Stuendlicher Aggressions-Messpunkt des GESAMTEN Universums (Welle 4).

    Aus den ``combat_reports`` des Fensters aggregiert (Kampfanzahl, Gesamt-Truemmer,
    eindeutige Angreifer). ``level`` ist der daraus gewichtete Aggressionswert, ``status``
    das daraus abgeleitete Band (peaceful|tense|war|apocalypse). Verlauf + Frontend-Anzeige;
    Treiber fuers Erwachen des Waechters. PK = volle Stunde (eine Zeile je Stunde)."""
    __tablename__ = "aggression_history"

    hour: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    combat_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_debris: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    unique_attackers: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    level: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    status: Mapped[str] = mapped_column(Text, default="peaceful", server_default="peaceful")


class AwakeningWarden(Base):
    """Der uralte Waechter „Der Erwachte" (Welle 4): server-weite, emergente Bedrohung.

    Erwacht, wenn das Aggressionsniveau ALLER Spieler eine Schwelle ueberschreitet, bedroht/
    greift die aggressivsten Imperien, funkt wuerdevoll-bedrohlich (KI) und beruhigt das
    Universum bei seiner Niederlage (+ Belohnung der Beteiligten). Der eigentliche KAMPF-
    Koerper ist ein ``NpcEmpire`` (``npc_id``) — so wird der bestehende Spieler<->NPC-Kampf
    UND die ``NpcAttack``-Infrastruktur wiederverwendet. Diese Zeile haelt nur den server-
    weiten Lebenszyklus-Zustand. Es existiert hoechstens EINE Zeile mit status='active'."""
    __tablename__ = "awakening_warden"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("npc_empires.id", ondelete="SET NULL"), nullable=True
    )
    spawned_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    aggression_level: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    fleet: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    target_scope: Mapped[str] = mapped_column(Text, default="global", server_default="global")
    # Freies Status-/Tracking-Feld: {"participants": [player_id,...], "threats": int, ...}.
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, default="active", server_default="active")  # active|defeated|dormant
    last_threat_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    defeated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Beruhigungs-Cooldown: bis dahin erwacht kein neuer Waechter (nach Niederlage/Rueckzug).
    calm_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EventBuff(Base):
    """Generischer temporärer Buff/Debuff aus einem Event. Multiplikativ (production/build_speed/
    research_speed), additiv (morale_adjust) oder reiner Schalter (scan_block/spionage_block).

    ``scope`` = 'player' | 'planet' | 'system'. Je nach Scope sind player_id ODER planet_id ODER
    (galaxy, system) gesetzt. Ablauf rein zeitlich (``expires_at``) — kein Job noetig, die Abfragen
    filtern ``expires_at > now``. Ein periodischer Tick raeumt nur abgelaufene Zeilen weg."""
    __tablename__ = "event_buffs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cosmic_events.id", ondelete="CASCADE"), nullable=True
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False)             # player|planet|system
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=True
    )
    planet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"), nullable=True
    )
    galaxy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    system: Mapped[int | None] = mapped_column(Integer, nullable=True)
    buff_type: Mapped[str] = mapped_column(Text, nullable=False)         # production|build_speed|...
    magnitude: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
