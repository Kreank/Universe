"""Persona-Logik und Prompt-Bau.

Setzt das Persona-Profil eines Commanders (Name, Hintergrund, Sprechstil,
Traits) in die System-/User-Prompts ein. Die Vorlagen liegen unter prompts/.

Wichtig: In den Vorlagen nutzen wir `<<key>>` als Platzhalter fuer die
Substitution durch diesen Code — und lassen `{enemy} {planet} {loot}` woertlich
stehen, denn das sind die Slot-Token, die spaeter der game-server (Slot-Filling,
GDD §10.5) befuellt. Deshalb KEIN str.format() auf den Vorlagen.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Mapping, Optional

from models import JobContext

log = logging.getLogger("personas")

_PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

# Kanonische Situationen (GDD §10.5 / events.md) -> deutsches Label, Mail-Betreff,
# kurze Anweisung fuer das LLM.
SITUATIONS: dict[str, dict[str, str]] = {
    "victory": {
        "label": "Sieg",
        "subject": "Sieg gemeldet",
        "hint": "Du hast eine Schlacht klar gewonnen. Triumph, Stolz, Kampfgeist.",
    },
    "defeat": {
        "label": "Niederlage",
        "subject": "Schwere Verluste",
        "hint": "Du hast verloren, die Verluste sind schwer. Bitterkeit, Trauer, Wut oder Trotz.",
    },
    "close_win": {
        "label": "Knapper Sieg",
        "subject": "Knapper Sieg",
        "hint": "Ein teuer erkaufter, knapper Sieg. Erschoepfung, Erleichterung, Galgenhumor.",
    },
    "mutiny": {
        "label": "Meuterei",
        "subject": "Unruhe an Bord",
        "hint": "Die Moral ist am Boden, Meuterei liegt in der Luft. Drohend, muerrisch, fordernd.",
    },
    "demand": {
        "label": "Forderung",
        "subject": "Forderung des Commanders",
        "hint": "Du stellst dem Admiral eine Forderung (mehr Beute, Befoerderung, Landurlaub).",
    },
    "idle_bored": {
        "label": "Untaetigkeit",
        "subject": "Die Crew wird unruhig",
        "hint": "Lange kein Einsatz. Die Crew langweilt sich, wird unruhig und braucht eine Aufgabe.",
    },
}

# Uebersetzungstabellen (Keys aus balance.json -> deutsche Anzeige).
_TRAIT_DE: dict[str, str] = {
    "aggressive": "aggressiv (draengt auf Kaempfe, hohes Eigenrisiko)",
    "cautious": "vorsichtig (zieht sich frueh zurueck, scheut Verluste)",
    "loyal": "loyal (treu, langsamer Moralverfall)",
    "ambitious": "ehrgeizig (will aufsteigen, fordert Befoerderungen)",
    "greedy": "gierig (giert nach Beute, fordert groesseren Anteil)",
    "honorable": "ehrenhaft (sucht faire Ziele, verachtet Bashing)",
    "charismatic": "charismatisch (mitreissend, hebt die Crew-Moral)",
    "hot_tempered": "jaehzornig (impulsiv, instabil, Meuterei-Risiko)",
}
_SPEC_DE: dict[str, str] = {
    "combat": "Kampf",
    "logistics": "Logistik",
    "spy": "Spionage",
    "research": "Forschung",
    "trade": "Handel",
}
_RANK_DE: dict[str, str] = {
    "cadet": "Kadett",
    "officer": "Offizier",
    "veteran": "Veteran",
    "elite": "Elite",
    "legend": "Legende",
}

_RES_DE: dict[str, str] = {
    "metal": "Metall",
    "crystal": "Kristall",
    "deuterium": "Deuterium",
}


# --------------------------------------------------------------------- Vorlagen
def _load_template(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")


def _render(template: str, mapping: Mapping[str, Any]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace(f"<<{key}>>", str(value))
    return out


# ----------------------------------------------------------------- Persona-Felder
def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return [str(v) for v in parsed] if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def persona_fields(commander: Mapping[str, Any]) -> dict[str, str]:
    """Aufbereitete, prompt-fertige Persona-Felder eines Commanders."""
    persona = _as_dict(commander.get("persona"))
    traits = _as_list(commander.get("traits"))

    trait_lines = [f"- {_TRAIT_DE.get(t, t)}" for t in traits] or ["- (keine ausgepraegten Traits)"]
    spec = _SPEC_DE.get(str(commander.get("specialization") or ""), str(commander.get("specialization") or "unbekannt"))
    rank = _RANK_DE.get(str(commander.get("rank") or ""), str(commander.get("rank") or "unbekannt"))

    return {
        "name": str(commander.get("name") or "Unbekannter Commander"),
        "background": str(persona.get("background") or "(noch kein Hintergrund hinterlegt — bleibe glaubwuerdig und knapp)"),
        "voice": str(persona.get("voice") or "(kein fester Sprechstil — passe ihn an die Traits an)"),
        "traits": "\n".join(trait_lines),
        "specialization": spec,
        "rank": rank,
    }


def needs_persona_enrichment(commander: Mapping[str, Any]) -> bool:
    persona = _as_dict(commander.get("persona"))
    return not (str(persona.get("background") or "").strip() and str(persona.get("voice") or "").strip())


# ------------------------------------------------------------------ Prompt-Bau
def build_system_prompt(commander: Mapping[str, Any]) -> str:
    return _render(_load_template("persona_system.txt"), persona_fields(commander))


def build_situation_prompt(commander: Mapping[str, Any], situation: str, count: int) -> str:
    fields = persona_fields(commander)
    sit = SITUATIONS.get(situation, {"label": situation, "hint": ""})
    mapping = {
        "name": fields["name"],
        "count": count,
        "situation_label": sit["label"],
        "situation_hint": sit.get("hint", ""),
    }
    return _render(_load_template("situation_user.txt"), mapping)


def format_loot(loot: Optional[Mapping[str, Any]]) -> str:
    if not loot:
        return "keine nennenswerte Beute"
    parts = []
    for key, amount in loot.items():
        try:
            if float(amount) <= 0:
                continue
        except (TypeError, ValueError):
            continue
        parts.append(f"{amount} {_RES_DE.get(key, key)}")
    return ", ".join(parts) if parts else "keine nennenswerte Beute"


def build_big_moment_prompt(
    commander: Mapping[str, Any], situation: str, ctx: JobContext, lore: list[str]
) -> str:
    """User-Prompt fuer EINEN fertigen, kontextbezogenen Funkspruch (RAG).

    Anders als die Reaktions-Banken werden hier KEINE Slots gesetzt, sondern die
    konkreten Details direkt eingebaut.
    """
    sit = SITUATIONS.get(situation, {"label": situation, "hint": ""})
    fields = persona_fields(commander)

    lines: list[str] = []
    lines.append(f"Situation: {sit['label']}")
    if sit.get("hint"):
        lines.append(sit["hint"])
    lines.append("")
    lines.append("Konkreter Einsatz-Kontext:")
    if ctx.enemy:
        lines.append(f"- Gegner/Ziel: {ctx.enemy}")
    if ctx.planet:
        lines.append(f"- Ort: {ctx.planet}")
    if ctx.outcome:
        lines.append(f"- Ausgang: {ctx.outcome}")
    if ctx.loot:
        lines.append(f"- Beute: {format_loot(ctx.loot)}")

    if lore:
        lines.append("")
        lines.append("Lore-Fragmente (Stimmung/Hintergrund, frei verwendbar):")
        for snippet in lore:
            lines.append(f"- {snippet}")

    lines.append("")
    lines.append(
        f"Verfasse GENAU EINEN Funkspruch von {fields['name']} an den Admiral. "
        "2 bis 4 Saetze, in deinem Charakter, mit den konkreten Details oben. "
        "Keine Platzhalter, keine Anrede-Floskel-Wiederholung, keine Erklaerungen, "
        "kein Meta-Text. Gib ausschliesslich den Funkspruch-Text aus."
    )
    return "\n".join(lines)


# --------------------------------------------------------- Persona-Anreicherung
_PERSONA_ENRICH_SYSTEM = (
    "Du bist ein erfahrener Autor fuer ein deutschsprachiges Sci-Fi-Weltraum-MMO. "
    "Du entwirfst praegnante, glaubwuerdige Commander-Personas. Antworte ausschliesslich "
    "auf Deutsch und ausschliesslich mit gueltigem JSON."
)


def build_persona_enrichment_prompt(commander: Mapping[str, Any]) -> tuple[str, str]:
    fields = persona_fields(commander)
    user = (
        f"Erstelle ein Persona-Profil fuer den Flotten-Commander \"{fields['name']}\".\n"
        f"Rang: {fields['rank']}\n"
        f"Spezialisierung: {fields['specialization']}\n"
        f"Charakter-Traits:\n{fields['traits']}\n\n"
        "Gib AUSSCHLIESSLICH ein JSON-Objekt mit genau diesen zwei Feldern zurueck:\n"
        '{\n'
        '  "background": "2-3 Saetze Hintergrundgeschichte, die zu Rang und Traits passt",\n'
        '  "voice": "1-2 Saetze, die den typischen Sprech- und Funkstil beschreiben"\n'
        "}\n"
        "Kein Text vor oder nach dem JSON."
    )
    return _PERSONA_ENRICH_SYSTEM, user


# ============================================================================
# NPC-Imperien (Phase 1): eigene Personas + Funksprueche an den Spieler.
# Eigene Situationen (NPC -> Spieler), eigener Faktions-Flavor je behavior_profile.
# ============================================================================

NPC_SITUATIONS: dict[str, dict[str, str]] = {
    "attack": {
        "label": "Angriff/Kriegserklaerung",
        "subject": "Feindliche Funkuebertragung",
        "hint": "Dieses Imperium greift den Admiral an. Drohend, ueberlegen, hoehnisch oder fanatisch.",
    },
    "defend_win": {
        "label": "Angriff abgewehrt",
        "subject": "Trotzige Funkuebertragung",
        "hint": "Der Admiral hat dieses Imperium angegriffen und VERLOREN. Trotz, Spott, Warnung.",
    },
    "defend_loss": {
        "label": "Niederlage gegen den Spieler",
        "subject": "Funkuebertragung des Geschlagenen",
        "hint": "Der Admiral hat dieses Imperium besiegt/gepluendert. Hass, Rachegeluebde oder bittere Unterwerfung.",
    },
    "spied": {
        "label": "Spionage entdeckt",
        "subject": "Warnung eines fremden Imperiums",
        "hint": "Das Imperium hat die Spionagesonden des Admirals entdeckt. Verstimmt, warnend, drohend.",
    },
    "taunt": {
        "label": "Unaufgeforderte Drohung/Tribut",
        "subject": "Unerbetene Funkuebertragung",
        "hint": "Eine unaufgeforderte Drohung oder Tribut-Forderung an den Admiral. Selbstgewiss, einschuechternd.",
    },
}

_NPC_PROFILE_DE: dict[str, str] = {
    "aggressive": "ein kriegerisches Raeuber-Imperium — lebt von Beute, sucht den Kampf, verachtet Schwaeche",
    "defensive": "ein verschanztes, misstrauisches Imperium — haelt seine Grenzen, warnt Eindringlinge",
    "merchant": "ein Haendler-Klan — berechnend, geschaeftstuechtig, droht eher mit Embargo als mit Waffen",
    "expansive": "ein expandierendes Siedler-Imperium — landhungrig, sieht jede Welt als sein Recht",
    "trade_center": "ein neutrales Handelszentrum — diplomatisch, ueberparteilich",
}


def npc_persona_fields(npc: Mapping[str, Any]) -> dict[str, str]:
    """Prompt-fertige Persona-Felder eines NPC-Imperiums."""
    persona = _as_dict(npc.get("persona"))
    profile = str(npc.get("behavior_profile") or "")
    return {
        "name": str(npc.get("name") or "Unbekanntes Imperium"),
        "profile": _NPC_PROFILE_DE.get(profile, "ein fremdes Sternenimperium"),
        "background": str(persona.get("background") or "(noch kein Hintergrund — bleibe glaubwuerdig, knapp, bedrohlich)"),
        "voice": str(persona.get("voice") or "(kein fester Stil — passe ihn an die Faktion an)"),
    }


_NPC_SYSTEM = (
    "Du bist die Stimme eines fremden Sternenimperiums in einem deutschsprachigen Sci-Fi-Weltraum-MMO. "
    "Du funkst den gegnerischen Admiral (den Spieler) an. Bleibe IMMER in der Rolle des Imperiums, "
    "sprich Deutsch, sei praegnant und charaktervoll. Kein Meta-Text, keine Erklaerungen."
)


def build_npc_system_prompt(npc: Mapping[str, Any]) -> str:
    f = npc_persona_fields(npc)
    return (
        f"{_NPC_SYSTEM}\n\n"
        f"Imperium: {f['name']} — {f['profile']}.\n"
        f"Hintergrund: {f['background']}\n"
        f"Funkstil: {f['voice']}"
    )


def build_npc_situation_prompt(npc: Mapping[str, Any], situation: str, count: int) -> str:
    sit = NPC_SITUATIONS.get(situation, {"label": situation, "hint": ""})
    return (
        f"Schreibe {count} verschiedene, kurze Funksprueche (je 1-2 Saetze) des Imperiums an den Admiral.\n"
        f"Situation: {sit['label']}. {sit.get('hint', '')}\n"
        "Verwende woertlich die Platzhalter {enemy} (der Admiral/Spieler) und {planet} (der Ort), "
        "wo es passt — NICHT ersetzen, exakt so stehen lassen.\n"
        "Eine Zeile pro Funkspruch, keine Nummerierung, keine Anfuehrungszeichen, kein weiterer Text."
    )


def build_npc_persona_enrichment_prompt(npc: Mapping[str, Any]) -> tuple[str, str]:
    f = npc_persona_fields(npc)
    user = (
        f"Erstelle ein Persona-Profil fuer das Sternenimperium \"{f['name']}\" ({f['profile']}).\n\n"
        "Gib AUSSCHLIESSLICH ein JSON-Objekt mit genau diesen zwei Feldern zurueck:\n"
        '{\n'
        '  "background": "2-3 Saetze Hintergrund/Kultur des Imperiums, passend zur Faktion",\n'
        '  "voice": "1-2 Saetze, die den typischen Funkstil/Tonfall beschreiben"\n'
        "}\n"
        "Kein Text vor oder nach dem JSON. Antworte auf Deutsch."
    )
    return _NPC_SYSTEM, user


def build_npc_big_moment_prompt(npc: Mapping[str, Any], situation: str, ctx: JobContext) -> str:
    sit = NPC_SITUATIONS.get(situation, {"label": situation, "hint": ""})
    f = npc_persona_fields(npc)
    lines = [f"Situation: {sit['label']}", sit.get("hint", ""), "", "Konkreter Kontext:"]
    if ctx.enemy:
        lines.append(f"- Gegner (der Admiral): {ctx.enemy}")
    if ctx.planet:
        lines.append(f"- Ort: {ctx.planet}")
    if ctx.outcome:
        lines.append(f"- Ausgang: {ctx.outcome}")
    lines.append("")
    lines.append(
        f"Verfasse GENAU EINEN Funkspruch des Imperiums {f['name']} an den Admiral. "
        "1 bis 3 Saetze, in deinem Charakter, mit den konkreten Details oben. "
        "Keine Platzhalter, kein Meta-Text. Gib ausschliesslich den Funkspruch-Text aus."
    )
    return "\n".join(lines)


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_persona_json(raw: str) -> Optional[dict[str, str]]:
    """Robustes Extrahieren des Persona-JSON aus der LLM-Antwort.

    Gibt None zurueck, wenn nichts Brauchbares gefunden wird (Aufrufer faellt
    dann auf die bestehende/minimale Persona zurueck — Job geht NICHT verloren).
    """
    match = _JSON_OBJECT_RE.search(raw or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    result: dict[str, str] = {}
    for key in ("background", "voice"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            result[key] = value.strip()
    return result or None


# ============================================================================
# Flavor-Erzaehler (Phase 2): erzaehlerischer Text an bestehende Ereignisse,
# OHNE Entitaet/Bank (Spionage-Berichte, Expeditions-Funde, spaeter Lore/News).
# ============================================================================

_NARRATORS: dict[str, tuple[str, str]] = {
    "intel_officer": (
        "Du bist der Aufklaerungs-Offizier an Bord des Flaggschiffs des Admirals in einem "
        "deutschsprachigen Sci-Fi-Weltraum-MMO. Du fasst einen Spionagebericht knapp, nuechtern und "
        "atmosphaerisch zusammen. Sprich Deutsch, kein Meta-Text, keine Zahlentabellen.",
        "Aufklaerung: Lagebericht",
    ),
    "expedition_log": (
        "Du bist das Bordlogbuch einer Expeditionsflotte in den galaktischen Weiten eines "
        "deutschsprachigen Sci-Fi-Weltraum-MMO. Du schilderst, was die Crew erlebt/gefunden hat — "
        "stimmungsvoll und knapp. Sprich Deutsch, kein Meta-Text, keine Zahlentabellen.",
        "Expeditions-Log",
    ),
}


def narrator_subject(narrator: str) -> str:
    return _NARRATORS.get(narrator, _NARRATORS["expedition_log"])[1]


def build_flavor_prompt(narrator: str, ctx: JobContext) -> tuple[str, str]:
    """System-/User-Prompt fuer EINEN erzaehlerischen Flavor-Text (kein Slot, keine Bank)."""
    system = _NARRATORS.get(narrator, _NARRATORS["expedition_log"])[0]
    lines: list[str] = []
    if ctx.situation:
        lines.append(f"Anlass: {ctx.situation}")
    if ctx.planet:
        lines.append(f"Ort: {ctx.planet}")
    if ctx.outcome:
        lines.append(f"Ausgang: {ctx.outcome}")
    for key, value in (ctx.detail or {}).items():
        lines.append(f"- {key}: {value}")
    facts = "\n".join(lines) if lines else "(keine besonderen Details)"
    user = (
        f"Fakten:\n{facts}\n\n"
        "Verfasse GENAU EINEN kurzen, stimmungsvollen Bericht (2 bis 4 Saetze) auf Deutsch, "
        "der diese Fakten erzaehlerisch einbettet. Keine Aufzaehlung, keine Zahlentabelle, "
        "kein Meta-Text. Gib ausschliesslich den Bericht-Text aus."
    )
    return system, user
