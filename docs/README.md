# *Universe* — Design-Dokumentation (Index)

> **Arbeitstitel:** Universe · **Stand:** 2026-06-06 · Solo-Projekt (mit KI-Entwicklung)
>
> Ein browserbasiertes Weltraum-Aufbau-MMO in der Tradition von OGame — mit **persistentem
> Universum (kein Reset)** und **lebendigen KI-Crews** (Commander mit Moral & LLM-Funksprüchen)
> als Alleinstellungsmerkmalen. Dies ist der Navigations-Hub für die gesamte Doku.

---

## Fundament

| Dokument | Inhalt |
|----------|--------|
| [Game Design Document](./GAME_DESIGN_DOCUMENT.md) | **Übersicht & Single Source of Truth** — Vision, Säulen, Kern-Loop, Commander/Moral, KI-Architektur, Scope, Entscheidungen |
| [Architektur](./ARCHITECTURE.md) | Technik: modularer Monolith + AI-Worker, Datenflüsse, DB-Schema, Skalierung, ADRs |

## System-Dokumente (Detail-Design)

| # | System | Kernpunkte |
|---|--------|------------|
| 01 | [Wirtschaft & Gebäude](./systems/01-economy-and-buildings.md) | Ressourcen/Produktion/Energie/Kosten, Akademie & Kommandozentrale, Decay |
| 02 | [Technologiebaum](./systems/02-technology-tree.md) | 4 Kategorien inkl. Führung & Crew, Astrophysik-Kolonie-Gate |
| 03 | [Schiffe & Einheiten](./systems/03-ships-and-units.md) | Roster, Rapidfire, Flaggschiff/Commander-Kopplung |
| 04 | [Kampfmodell](./systems/04-combat-model.md) | Rundenkampf, Moral/Traits, Flaggschiff→Permadeath/Capture |
| 05 | [Commander-Tiefe](./systems/05-commanders.md) | Ränge, Traits, Moral-Modell, Span, Fähigkeiten, Forderungen |
| 06 | [Universum & Karte](./systems/06-universe-and-map.md) | Koordinaten, Monde, Frontier-Ringe (Kern/Mitte/Frontier) |
| 07 | [Flottenmissionen](./systems/07-fleet-missions.md) | Missionstypen, Fleetsave+Bunker, Expeditionen, Commander-XP |
| 08 | [NPC-Imperien & PvE](./systems/08-npc-empires.md) | Behavior-Tree-KI, reiche PvE-Ebene, voll dynamische NPCs |
| 09 | [Allianzen & Diplomatie](./systems/09-alliances-and-diplomacy.md) | Rollen, ACS+Span-Bündelung, Territorium, Kriegsmüdigkeit |
| 10 | [Progression & Pacing](./systems/10-progression-and-pacing.md) | Phasen, Scoring, Saisons, starke Aufhol-Mechaniken |
| 11 | [Spielererlebnis (UX)](./systems/11-player-experience.md) | Screens, Commander-Hub, Onboarding, Web + native App |
| 12 | [Fairness & Monetarisierung](./systems/12-fairness-and-monetization.md) | Kein P2W, Anti-Cheat, Multi-Account/Pushing-Regeln |

---

## Getroffene Kern-Entscheidungen (Schnellüberblick, Stand 2026-06-06)

**Spielwelt & Pacing**
- Persistentes Universum, **kein Reset**; konzentrische Ringe (Kern/Mitte/Frontier);
  **bevölkerungsbasierte** Frontier-Expansion.
- **Universe-Speed ×5–10** (modern/zugänglich); Kurven-Steilheit im Prototyp tunen.
- Saison: nur Ranglisten/Score/Belohnungen reset, **Imperium bleibt** (quartalsweise).
- **Starke Aufhol-Mechaniken**; **Hybrid**-Motivation (Saison-Ziele + Sandbox).

**Commander (USP)**
- **Echter Permadeath** mit Leitplanken (Evakuierung **nur wenn Schiffe überleben**,
  Neulingsschutz, progressiver Rang-Schutz); Flaggschiff-Verlust koppelt an Permadeath/Capture.
- Beschaffung über **alle Pfade** (Akademie + Anwerben + Gefangennahme + Bergung +
  Beförderung); Anzahl = **emergenter Soft-Cap** (Start 1, Midgame ~3–5).
- **Kein Sold** — Moral nur durch Taten; **Moral-Verfall bei Vernachlässigung** als Horten-Bremse.
- **Schlanke** Progression (Rang + Traits); Traits mit **Vor- und Nachteilen**.
- Kampf: **aktive Fähigkeiten** + Moral-/Trait-Modifikatoren.

**Forschung, Schiffe, Welt**
- **Eine Forschung gleichzeitig** (IRN für Tempo); Kolonien via **Astrophysik-Gate**.
- Superschiff (Todesstern) **ja, hart gegatet**.
- **Monde** mit Phalanx/Sprungtor (Default ja).
- Fleetsave **klassisch + Bunker-Option**; Expeditionen = **Hauptsäule für Funde**,
  getrennt von Kolonisierung.

**Sozial, NPC, Fairness**
- **Voll dynamische** NPC-Imperien; **reiche PvE-Ebene**.
- Allianzen mit **formellem Territorium** + **Megaprojekten**; ACS-Span-Bündelung; Kriegsmüdigkeit.
- **Web (Angular) + native Mobile-App**; Benachrichtigungen **In-App + Push**.
- **Kein P2W**: Kosmetik + QoL + gedeckelte Zeit-Beschleunigung; Premium-Währung auch
  ingame verdienbar; **tolerante Multi-Account-Politik** mit strengen Anti-Pushing-Regeln.

> Offene Feintuning-Punkte (Zahlenwerte) sind in den jeweiligen Doku-§ „Tuning-Hebel"
> sowie GDD §12.2 gesammelt und werden im **Prototyp** entschieden.

---

## Empfohlene nächste Schritte

1. **Repo-Scaffold** — Struktur aus [Architektur §10](./ARCHITECTURE.md) als echte Dateien
   (Docker-Compose, FastAPI-Skelett, Angular-Init, init-SQL).
2. **Vertical Slice** bauen (GDD §13) und dabei die offenen Zahlenwerte tunen.
3. Detail-Dokus iterativ verfeinern, sobald der Prototyp echtes Spielgefühl liefert.
