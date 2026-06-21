#!/usr/bin/env python3
"""Mk-II-Generator (Welle W3 — Endgame-Veredelung).

Liest ``shared/balance.json`` und ergaenzt fuer JEDES regulaere Schiff einen
``<typ>_mk2``-Eintrag (Kampf/Rollen/zivil). Capstone-Schiffe (Key ``capstone``)
sind ausgenommen — sie sind bereits Endgame. Ableitung aus ``ships._mk2_factors``:

  * Nutzen-Werte attack/shield/cargo/speed -> × jeweiliger Faktor, gerundet (int),
    nur falls am Schiff vorhanden. So ist ein Mk2 +25% besser in seiner ROLLE:
    ein Transporter laedt mehr (cargo), ein Kampfschiff schiesst/fliegt staerker.
  * cost.{metal,crystal,deuterium} -> × cost-factor (int)
  * cost.antimatter -> round(antimatter_pct × (metal+crystal) der Mk1-Kosten)
  * fuel       -> × fuel-factor (hoeherer Verbrauch = Nachteil)
  * fuel_tank  -> × fuel_tank-factor (Tank waechst mit)
  * rapidfire  -> vom Mk1 uebernommen (KEIN Remapping auf Mk2-Ziele!)
  * requires   -> Mk1.requires + { "veteran_shipyard": 1 }
  * mk2_parent -> "<typ>"

Zusaetzlich wird das Kampfprofil (``combat_roster[<typ>]``) 1:1 auf
``combat_roster[<typ>_mk2]`` kopiert (weapon_type/drive/range + Rollen-Flags),
damit die Engine das Mk-II nicht still auf das kinetic/near-Default zurueckfallen
laesst (test_every_unit_has_a_combat_roster_entry). Etwaige ``aura``-Keys werden
nicht uebernommen (Auren sind capstone-exklusiv; Capstones sind ohnehin ausgenommen).

IDEMPOTENT: legt nie ein Mk2 eines Mk2 an, ueberspringt bereits vorhandene
``<typ>_mk2``-Eintraege und schreibt nur, wenn sich etwas geaendert hat. Die Datei
wird textchirurgisch ergaenzt (bestehende Formatierung bleibt unangetastet).

Aufruf:  python3 scripts/gen_mk2.py [--check | --force]
  --check  : nichts schreiben, nur melden, wie viele Eintraege fehlen (Exit 1 falls welche fehlen).
  --force  : REGENERATE — entfernt zuerst ALLE vorhandenen ``*_mk2``-Schiffe UND
             ``combat_roster.*_mk2``-Profile (Textchirurgie) und erzeugt sie dann
             mit den AKTUELLEN ``_mk2_factors`` neu. Noetig, wenn sich Faktoren
             aendern (der Normallauf ueberspringt Bestehende = idempotent).
"""
from __future__ import annotations

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BALANCE_PATH = os.environ.get("BALANCE_PATH") or os.path.normpath(
    os.path.join(HERE, "..", "shared", "balance.json")
)
MK2_SUFFIX = "_mk2"
# Nutzen-Werte, die ein Mk2 in seiner ROLLE besser machen (jeweils ×eigener Faktor).
BENEFIT_KEYS = ("attack", "shield", "cargo", "speed")


def _is_real(name: str, cfg: object) -> bool:
    """Echter Katalog-Eintrag (kein ``_``-Meta-Key, ein Dict)."""
    return not name.startswith("_") and isinstance(cfg, dict)


def derive_mk2(name: str, cfg: dict, factors: dict) -> dict:
    """Leitet den Mk-II-Eintrag eines Mk1-Schiffs nach den Faktoren ab."""
    f_cost = float(factors["cost"])
    f_fuel = float(factors["fuel"])
    f_tank = float(factors.get("fuel_tank", factors["fuel"]))
    am_pct = float(factors["antimatter_pct"])

    mk2 = copy.deepcopy(cfg)

    # Nutzen-Werte: jeder am Schiff vorhandene Wert ×eigener Faktor (+25% besser in der Rolle).
    # Nur anfassen, was das Schiff auch hat (ein reiner Transporter ohne attack bleibt ohne attack).
    for key in BENEFIT_KEYS:
        if key in cfg and key in factors:
            mk2[key] = int(round(cfg[key] * float(factors[key])))

    base_cost = cfg.get("cost", {})
    cost = {}
    for k in ("metal", "crystal", "deuterium"):
        cost[k] = int(round(base_cost.get(k, 0) * f_cost))
    antimatter = int(round(am_pct * (base_cost.get("metal", 0) + base_cost.get("crystal", 0))))
    if antimatter > 0:
        cost["antimatter"] = antimatter
    mk2["cost"] = cost

    if "fuel" in cfg:
        mk2["fuel"] = int(round(cfg["fuel"] * f_fuel))
    if "fuel_tank" in cfg:
        mk2["fuel_tank"] = int(round(cfg["fuel_tank"] * f_tank))

    # rapidfire wird durch den deepcopy uebernommen (Mk1-Ziele bleiben — kein Mk2-Remapping).
    mk2["requires"] = {**cfg.get("requires", {}), "veteran_shipyard": 1}
    mk2["mk2_parent"] = name
    mk2.pop("capstone", None)  # Sicherheit; Capstones werden ohnehin nicht verarbeitet.
    return mk2


def plan(data: dict) -> tuple[list[tuple[str, dict]], list[tuple[str, dict]]]:
    """Bestimmt fehlende (ship, roster)-Eintraege. Reine Funktion (kein I/O)."""
    ships = data["ships"]
    roster = data.get("combat_roster", {})
    factors = ships["_mk2_factors"]

    new_ships: list[tuple[str, dict]] = []
    new_roster: list[tuple[str, dict]] = []
    for name, cfg in list(ships.items()):
        if not _is_real(name, cfg):
            continue
        if cfg.get("capstone"):           # Capstones bleiben ausgenommen.
            continue
        if name.endswith(MK2_SUFFIX) or "mk2_parent" in cfg:  # kein Mk2 vom Mk2.
            continue
        mk2_name = f"{name}{MK2_SUFFIX}"
        if mk2_name not in ships:
            new_ships.append((mk2_name, derive_mk2(name, cfg, factors)))
        if mk2_name not in roster and isinstance(roster.get(name), dict):
            prof = copy.deepcopy(roster[name])
            prof.pop("aura", None)        # Auren sind capstone-exklusiv.
            new_roster.append((mk2_name, prof))
    return new_ships, new_roster


# ----------------------------------------------------------------- Textchirurgie

def _format_entry(name: str, entry: dict, base_indent: int) -> str:
    """Serialisiert ``"name": {...}`` mit ``base_indent`` Leerzeichen vor dem Key
    (Inhalt entsprechend tiefer), passend zur 2-Space-Formatierung der Datei."""
    pad = " " * base_indent
    dump = json.dumps(entry, ensure_ascii=False, indent=2)
    lines = dump.split("\n")
    out = f'{pad}"{name}": {lines[0]}'
    for ln in lines[1:]:
        out += f"\n{pad}{ln}"
    return out


def _object_close_index(text: str, key: str) -> int:
    """Index des schliessenden ``}`` des Objekts, das auf ``"key": {`` folgt."""
    start = text.index(f'"{key}": {{')
    i = text.index("{", start)
    depth = 0
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"Kein schliessendes }} fuer {key} gefunden")


def _insert_entries(text: str, key: str, entries: list[tuple[str, dict]], indent: int) -> str:
    """Fuegt ``entries`` als letzte Mitglieder des Objekts ``key`` ein (vor dessen ``}``)."""
    if not entries:
        return text
    close = _object_close_index(text, key)
    # Whitespace/Newline vor der schliessenden Klammer abtrennen.
    j = close
    while j > 0 and text[j - 1] in " \t":
        j -= 1
    block = ",\n" + ",\n".join(_format_entry(n, e, indent) for n, e in entries) + "\n"
    return text[:j] + block + text[j:]


def _remove_entry(text: str, key: str, name: str) -> str:
    """Entfernt den Eintrag ``"name": {...}`` (inkl. zugehoerigem Komma) aus dem
    Objekt ``key`` per Textchirurgie. Sucht NUR innerhalb von ``key`` (gleicher
    Name kann in ``ships`` und ``combat_roster`` vorkommen)."""
    obj_start = text.index(f'"{key}": {{')
    obj_close = _object_close_index(text, key)
    idx = text.index(f'"{name}": {{', obj_start, obj_close)
    # Schliessende Klammer dieses Eintrags via Tiefenzaehlung finden.
    i = text.index("{", idx)
    depth = 0
    end = -1
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
        i += 1
    if end < 0:
        raise ValueError(f"Kein schliessendes }} fuer {name} gefunden")
    line_start = text.rfind("\n", 0, idx) + 1
    after = end + 1
    if after < len(text) and text[after] == ",":
        # Folge-Eintrag vorhanden: Eintrag + Komma + Zeilenumbruch entfernen.
        after += 1
        if after < len(text) and text[after] == "\n":
            after += 1
        return text[:line_start] + text[after:]
    # Letzter Eintrag im Objekt: vorangehendes Komma mit entfernen.
    j = line_start - 1
    while j > 0 and text[j] in " \t\r\n":
        j -= 1
    if text[j] == ",":
        return text[:j] + text[end + 1:]
    return text[:line_start] + text[end + 1:]


def _remove_entries(text: str, key: str, names: list[str]) -> str:
    for name in names:
        text = _remove_entry(text, key, name)
    return text


def main() -> int:
    check_only = "--check" in sys.argv
    force = "--force" in sys.argv or "--regenerate" in sys.argv
    with open(BALANCE_PATH, encoding="utf-8") as fh:
        text = fh.read()
    data = json.loads(text)

    if force and not check_only:
        ships = data["ships"]
        roster = data.get("combat_roster", {})
        ship_mk2 = [k for k, v in ships.items() if k.endswith(MK2_SUFFIX) and _is_real(k, v)]
        roster_mk2 = [k for k in roster if k.endswith(MK2_SUFFIX)]
        text = _remove_entries(text, "ships", ship_mk2)
        text = _remove_entries(text, "combat_roster", roster_mk2)
        data = json.loads(text)  # neu parsen, damit plan() die entfernten wieder einplant
        print(f"Mk2 regenerate: {len(ship_mk2)} Schiffe + {len(roster_mk2)} Roster-Profile entfernt.")

    new_ships, new_roster = plan(data)
    total = len(new_ships)
    if not new_ships and not new_roster:
        print(f"Mk2: nichts zu tun ({BALANCE_PATH}) — alle Eintraege vorhanden.")
        return 0

    if check_only:
        print(f"Mk2 FEHLEN: {len(new_ships)} Schiffe, {len(new_roster)} Roster-Profile.")
        for n, _ in new_ships:
            print("  ship  ", n)
        for n, _ in new_roster:
            print("  roster", n)
        return 1

    text = _insert_entries(text, "ships", new_ships, indent=4)
    text = _insert_entries(text, "combat_roster", new_roster, indent=4)

    # Validitaet sicherstellen, bevor geschrieben wird.
    json.loads(text)
    with open(BALANCE_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)

    print(f"Mk2 geschrieben: {len(new_ships)} Schiffe + {len(new_roster)} Roster-Profile -> {BALANCE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
