"""Ziele/Bedrohungen-Domaene (Welle 1, Frontend-Konsistenz-Epos).

Buendelt die aus der Galaxie ausgelagerten Ziel-Listen: entdeckte NPC-Imperien,
entdeckte fremde Spieler und aktuelle Bedrohungen (eingehende Angriffe + feindliche
NPCs in der Naehe). Reine Auswahl-/Sortierlogik liegt in ``service`` und ist
DB-frei testbar (siehe tests/test_targets.py)."""
