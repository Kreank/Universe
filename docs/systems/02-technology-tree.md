# System-Design: Technologiebaum (Forschung)

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · baut auf [01 Wirtschaft & Gebäude](./01-economy-and-buildings.md)
>
> Forschung ist die zweite Fortschrittsachse neben Gebäuden. Sie schaltet Schiffe,
> Antriebe, Kampfboni, Kolonien und ⭐ Commander-Fähigkeiten frei. Basis: OGame-Techbaum;
> Abweichungen markiert (🔧 = Tuning-Hebel, ⭐ = Universe-spezifisch).

---

## 1. Designziele

1. **Spezialisierung ermöglichen.** Der Techbaum ist der Hauptweg, auf dem sich die drei
   Spielstile (Forscher/Militär/Händler, GDD §5) ausprägen.
2. **Gated Progression.** Forschung ist „Schlüssel" — ohne die richtige Tech kein
   Schlachtschiff, keine Kolonie, kein weiter Flug. Erzeugt Planungstiefe.
3. **Langfrist-Sinks.** Hochstufige Boni-Techs (Waffen/Schild/Plasma) sind Ressourcen-
   Senken fürs Late-Game und halten Fortschritt offen, ohne ins Unendliche zu skalieren.

---

## 2. Forschungsmechanik

- **Forschungslabor** (Gebäude, Doku 01) ist Voraussetzung; seine Stufe beschleunigt
  Forschung.
- **Forschungszeit (Stunden):** `(Metall + Kristall) / (1000 × (1 + Labor-Lvl) × Speed)`
  (Speed = Universe-Speed ×5–×10, Doku 01 §9).
- **Kostenskalierung:** `Basis × 2^(lvl−1)` (Standard; einzelne Techs abweichend, 🔧).
- **Intergalaktisches Forschungsnetzwerk (IRN):** verbindet die Labore mehrerer Planeten,
  sodass ihre Stufen für die Forschungsgeschwindigkeit zusammenzählen. Wichtiger Late-Game-
  Beschleuniger und Anreiz für Mehrplaneten-Wirtschaft.

> **Offener Fork (Konkurrenz):** Wie viele Forschungen gleichzeitig?
> *Klassisch:* genau **eine** zur Zeit (strategischer, klare Prioritäten). *Modern:* mehrere
> parallel / pro Planet (schneller, weniger Flaschenhals). → Entscheidung in §7.

---

## 3. Forschungskategorien

### 3.1 Antriebe & Reichweite (für Forscher/Erkunder & alle Flotten)
| Tech | Effekt | Wichtige Voraussetzung |
|------|--------|------------------------|
| **Energietechnik** | Grundlage vieler Techs; bessere Fusion | Labor 1 |
| **Verbrennungstriebwerk** | +Tempo kleiner Schiffe | Energietechnik 1 |
| **Impulstriebwerk** | +Tempo mittlerer Schiffe | Energietechnik 1 |
| **Hyperraumtechnik** | Grundlage Hyperraumantrieb & große Schiffe | Energietechnik 5 |
| **Hyperraumantrieb** | +Tempo großer Schiffe; Reichweite | Hyperraumtechnik 3 |
| **Spionagetechnik** | bessere Aufklärung, schwerer auszuspionieren | Labor 3 |
| **Computertechnik** | **+1 Flottenslot** je Stufe | Labor 1 |
| **Astrophysik** ⭐ | schaltet Kolonien & Expeditionen frei (§5) | Spionage 4, Impuls 3 |

### 3.2 Kampftechnik (für Militär/Piraterie)
| Tech | Effekt |
|------|--------|
| **Waffentechnik** | +10 % Waffenstärke je Stufe (alle Einheiten) |
| **Schildtechnik** | +10 % Schildstärke je Stufe |
| **Raumschiffpanzerung** | +10 % Hüllenstärke je Stufe |
| **Lasertechnik / Ionentechnik / Plasmatechnik** | schalten stärkere Waffensysteme & Schiffe frei |
| **Gravitontechnik** | Voraussetzung für Superschiff (Todesstern-Äquivalent); extrem energieintensiv |

### 3.3 Infrastruktur & Produktion (für Händler & alle)
| Tech | Effekt |
|------|--------|
| **Plasmatechnik** | **+Produktion** (≈ +1 % Metall / +0,66 % Kristall / +0,33 % Deut je Stufe) |
| **Intergalaktisches Forschungsnetzwerk** | verbindet Labore (§2) |
| **Astrophysik** ⭐ | mehr Kolonien = mehr Wirtschaft (§5) |

### 3.4 ⭐ Führung & Crew (Universe-spezifisch — koppelt an Commander-System, GDD §6)
| Tech | Effekt |
|------|--------|
| **Kommandodoktrin** | erhöht **Span-of-Control** weiter (zusätzlich zur Kommandozentrale) |
| **Logistiktechnik** | schnellere **Moral-Erholung**, geringere Überdehnungs-Strafe |
| **Crew-Psychologie** | hebt die **Moral-Obergrenze** / verlangsamt Moral-Verfall (Horten-Bremse milder) |
| **Kommunikationstechnik** | größere Funk-Reichweite; ⭐ schnellere/tiefere Commander-Funksprüche (mehr Bank-Varianten) |

> Diese Kategorie ist unser Alleinstellungsmerkmal im Techbaum. Sie macht „Forschung" auch
> für den Führungs-/Crew-Aspekt relevant, nicht nur für Schiffe.

---

## 4. Abhängigkeits-Überblick (Kernketten)

```
Energietechnik ─┬─ Verbrennungstriebwerk
                ├─ Impulstriebwerk ──┐
                ├─ Lasertechnik ─ Ionentechnik ─ Plasmatechnik
                └─ Hyperraumtechnik ─ Hyperraumantrieb
Spionagetechnik ─┐
                 └─(+ Impuls 3) ─ Astrophysik ⭐ ─ Kolonien / Expeditionen
Computertechnik ─ Flottenslots
Waffen- / Schild- / Panzerungstechnik ─ Kampfstärke (linear, Langzeit-Sink)
Führung & Crew ⭐ ─ Span / Moral / Funk   (parallel, koppelt an Commander)
```

---

## 5. Kolonien & Astrophysik ⭐

Wichtig fürs persistente Universum & Frontier-Konzept (GDD §7):

- **Astrophysik** ist das Gate für neue Kolonien. Vorschlag (🔧): je **2 Stufen +1
  Kolonie-Slot** — begrenzt Expansion sinnvoll und macht Forschung zur Voraussetzung
  fürs Reichswachstum.
- Astrophysik schaltet außerdem **Expeditionen** frei (Erkundungsmissionen ins Unbekannte
  → Funde, Ressourcen, Commander-Bergung; Details System-Doku 07 Flottenmissionen).
- 🔧 Kolonie-Cap-Kurve abstimmen mit Frontier-Expansion und Decay, damit die Karte weder
  verstopft noch leer wirkt.

---

## 6. Forschung & Spielstil-Identität

| Spielstil | typische Forschungs-Schwerpunkte |
|-----------|----------------------------------|
| **Forscher/Erkunder** | Antriebe, Astrophysik, Spionage, Expeditionen, Crew-Psychologie |
| **Militär/Piraterie** | Waffen/Schild/Panzerung, Plasma/Ion/Laser, Hyperraumantrieb, Kommandodoktrin |
| **Wirtschaft/Handel** | Plasmatechnik, IRN, Astrophysik, Logistiktechnik, Computertechnik |

→ Kein Zwang: Mischen ist möglich, aber Fokus bringt schneller Schlagkraft im gewählten Pfad.

---

## 7. Tuning-Hebel & offene Entscheidungen 🔧

1. **Forschungs-Konkurrenz** — ✅ **Entscheidung (2026-06-06): eine Forschung gleichzeitig**
   pro Account, Labore via IRN für Tempo verbunden. Klare Prioritäten = mehr Strategie.
2. **Kolonie-Cap** — ✅ **Entscheidung (2026-06-06): Astrophysik-Gate**, +1 Kolonie-Slot
   je 2 Astrophysik-Stufen (exakte Kurve → Prototyp). Expansion ist eine Forschungs-Investition.
3. **Tiefe der ⭐ Führung-&-Crew-Techs jetzt** — voll ausarbeiten oder schlank als
   Platzhalter, bis Commander-Detail (Doku 05) steht? → schlank halten, finalisieren mit Doku 05.
4. **Boni-Tech-Deckel** — sollen Waffen/Schild/Panzerung/Plasma einen Soft-Cap haben
   (gegen Late-Game-Runaway, unterstützt Anti-Bashing)? Default: kein harter Cap, aber
   teure Kurve. → Prototyp.

---

## 8. Abhängigkeiten zu anderen System-Dokus

- **01 Wirtschaft** — Labor, Forschungszeit, Plasma-Produktionsbonus.
- **03 Schiffe** — fast jedes Schiff hat Tech-Voraussetzungen.
- **04 Kampf** — Waffen/Schild/Panzerung gehen direkt in die Kampfwerte.
- **06 Universum / 07 Missionen** — Astrophysik → Kolonien & Expeditionen.
- **GDD §6 Commander** — Führung-&-Crew-Techs modifizieren Span & Moral.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Forschungsmechanik (Zeit/Kosten/IRN), vier Kategorien
  inkl. ⭐ Führung & Crew, Abhängigkeitsketten, Astrophysik/Kolonien, Spielstil-Kopplung,
  Tuning-Hebel.
