# System-Design: Allianzen & Diplomatie

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · vertieft GDD §9 · koppelt an [07 Missionen](./07-fleet-missions.md), [06 Universum](./06-universe-and-map.md)
>
> Das soziale Endgame: wie Spieler sich zusammenschließen, kooperieren, Diplomatie betreiben
> und Kriege führen. ⭐ = Universe-spezifisch.

---

## 1. Designziele

1. **Kooperation lohnt sich.** Die drei Spielstile (Forscher/Militär/Händler, GDD §5)
   ergänzen sich erst in der Allianz zu einem vollständigen „Reich".
2. **Konflikt mit Struktur.** Diplomatie & Territorium geben PvP einen Rahmen
   (Kriege, Pakte) statt willkürlichem Bashing (GDD §8).
3. **⭐ Krieg hat menschliche Kosten.** Über Commander-Moral (Kriegsmüdigkeit) wird auch
   großflächiger Dauerkrieg organisch gebremst.

---

## 2. Gründung, Rollen & Rechte

- **Gründung/Beitritt:** Allianz mit Name + Tag erstellen; Mitglieder einladen/bewerben.
- **Rang-System mit Rechten** (konfigurierbar): z. B. Einladen/Kicken, Diplomatie verwalten,
  Allianz-Bank verwalten, ACS leiten, interne Ränge/Titel.
- **Kommunikation:** Allianz-Chat/-Forum, geteilte Karten-Marker, interne Rundsprüche.

---

## 3. Allianz-Strukturen

| Struktur | Funktion |
|----------|----------|
| **Allianzdepot** | erlaubt verbündeten Flotten **Nachtanken** am eigenen Planeten (verlängert Reichweite gemeinsam) |
| **Allianz-Bank** | gemeinsamer Ressourcen-Pool für Projekte/Hilfe |
| **Geteilte Karten-Intelligenz** | gebündelte Spionage-/Phalanx-Daten (Doku 04/06) |

---

## 4. Diplomatie

| Status | Bedeutung |
|--------|-----------|
| **Nichtangriffspakt (NAP)** | Zusage, sich nicht anzugreifen |
| **Bündnis** | gegenseitige Verteidigung (ACS-Verteidigung erlaubt/erwartet) |
| **Handelsabkommen** | bevorzugte Kurse/Routen (Doku 01 Wirtschaft) |
| **Krieg** | offizielle Kriegserklärung → Statistik-Tracking, ggf. Lockerung bestimmter Schutzmechaniken **zwischen den Kriegsparteien** (nicht ggü. Unbeteiligten/Neulingen) |

- **⭐ LLM-Diplomatie:** Verhandlungen mit **NPC-Imperien** (Doku 08) laufen als seltene
  LLM-Großmomente (Bündnisangebot, Drohung, Lösegeld; Architektur §5.4, GDD §10.2).

---

## 5. ACS — Koordinierte Operationen

Das taktische Kernstück des Miteinanders (Doku 07 §3):

- **ACS-Angriff:** mehrere Mitglieder timen ihre Flotten auf **dasselbe Ziel zur selben
  Ankunftszeit** → gebündelte Schlagkraft gegen befestigte Gegner.
- **ACS-Verteidigung (Halten):** Mitglieder stationieren Flotten beim Angegriffenen.
- **⭐ Commander-Synergie:** Im ACS zählt die Summe der Span-of-Control der beteiligten
  Commander — so umgeht koordinierte *Zusammenarbeit* das Einzel-Span-Limit (GDD §6.4)
  legitim. Belohnt echtes Teamspiel statt Solo-Blobbing.

---

## 6. ⭐ Territorium / Einflusszonen (Fork)

Optionale Tiefe: Allianzen kontrollieren **Regionen** (passt zu Distanz/Nähe, Doku 06):

- **Einfluss** über Systeme/Sektoren → kleine Boni (z. B. schnellere Erholung, Markt,
  Verteidigungsvorteil) und sichtbare „Grenzen" auf der Karte.
- **Umkämpfbar:** Einfluss kann durch Präsenz/Siege verschoben werden → strukturierte
  Großkonflikte statt zufälligem Geplänkel.
- *Trade-off:* viel Endgame-Tiefe, aber spürbarer Mehraufwand (Balancing, UI).

> 🔧 **Fork:** formelles Territorial-/Sovereignty-System vs. informell (Allianz = nur
> Gruppierung + Diplomatie + ACS). → §9.

---

## 7. ⭐ Kriegsmüdigkeit (Commander/Moral-Kopplung)

Verbindet das soziale System mit dem USP:

- Langer **Dauerkrieg** ohne Erfolge/Pausen senkt die **Moral** der beteiligten Commander
  (Überdehnung, Doku 05 §4) → großflächige Aggression bestraft sich mit der Zeit selbst.
- Erfolge, Friedensschlüsse und Erholung heben sie wieder.
- Effekt: Kriege haben einen natürlichen „Atem" (Eskalation → Erschöpfung → Frieden) statt
  endlosem Zermürben — unterstützt Anti-Bashing auf Makro-Ebene.

---

## 8. Allianz-Progression & Scoring

- Allianz-Ranglisten (Gesamt, Militär, Wirtschaft, Forschung) und **Saison-Ziele**
  (GDD §7.3) → kollektive Wettkampf-Anreize. Details Doku 10 Progression.

---

## 9. Tuning-Hebel & offene Entscheidungen 🔧

1. **Territorial-/Sovereignty-System:** ✅ **Entscheidung (2026-06-06): formelles
   Territorium** — umkämpfbare Einflusszonen mit Boni & sichtbaren Grenzen. Tiefes Endgame;
   wegen Aufwand ggf. erst nach dem Kern-Release ausrollen.
2. **Allianz-Megaprojekte:** ✅ **Entscheidung (2026-06-06): ja** — gemeinsame Großprojekte
   (geteilte Forschung, Allianz-Bauwerk/Relais mit Reichsboni) als kollektives Ziel, das
   alle drei Spielstile einbindet.
3. **Rang-Rechte-Granularität, ACS-Timing-Toleranz, Kriegs-Schutzlockerungen,
   Einflusswerte** → Prototyp.

---

## 10. Abhängigkeiten zu anderen System-Dokus

- **07 Missionen** — ACS-Angriff/-Verteidigung, Halten, Depot-Nachtanken.
- **06 Universum** — Nähe/Distanz, Territorium, Sprungtore (Mond).
- **05 Commander** — Span-Bündelung im ACS, Kriegsmüdigkeit/Moral.
- **08 NPC-Imperien** — LLM-Diplomatie, NPC-Kriege/-Pakte.
- **10 Progression** — Allianz-Ranglisten & Saison-Ziele.
- **GDD §9/§8/§10.2** — Allianz-Grundlagen, Anti-Bashing, KI-Diplomatie.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Gründung/Rollen, Strukturen (Depot/Bank/Karten-Intel),
  Diplomatie (NAP/Bündnis/Handel/Krieg + LLM-NPC-Diplomatie), ACS mit ⭐ Span-Bündelung,
  ⭐ Territorium-Fork, ⭐ Kriegsmüdigkeit, Allianz-Scoring, Tuning-Hebel.
