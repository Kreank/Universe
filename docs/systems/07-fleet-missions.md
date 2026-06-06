# System-Design: Flottenmissionen

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · baut auf [03 Schiffe](./03-ships-and-units.md), [06 Universum](./06-universe-and-map.md), koppelt an [04 Kampf](./04-combat-model.md)
>
> Alles, was Flotten tun: Missionstypen, Reise/Sprit/Slots, Rückruf, Expeditionen — und wie
> Commander dabei eingebunden sind. Basis: OGame-Missionen; ⭐ = Universe-spezifisch.

---

## 1. Designziele

1. **Reise ist eine Entscheidung.** Zeit, Sprit, Reichweite und Risiko machen jeden Flug
   zur Abwägung — nicht zum Klick.
2. **Verteidigung durch Geschick.** Spieler können ihre Flotte aktiv in Sicherheit bringen
   (Fleetsave) → Verluste sind vermeidbar, wer aufpasst (Kern der Genre-Spannung).
3. **⭐ Commander geben Missionen Charakter.** Wer die Flotte führt, beeinflusst Tempo,
   Sprit, Erfolg und Story — und sammelt dabei XP.

---

## 2. Flottenmechanik

- **Flottenslots:** `1 + Computertechnik-Stufe` (Doku 02) gleichzeitige Flüge.
  **Expeditionsslots** separat (über Astrophysik).
- **Tempo:** das **langsamste Schiff** bestimmt das Flottentempo. Man kann **gedrosselt**
  fliegen (z. B. 10–100 %), um **Sprit zu sparen** (langsamer = sparsamer).
- **Sprit (Deuterium):** Funktion aus **Distanz × Schiffe × Tempo** (Distanzklassen Doku 06).
- **Flugzeit:** hin und (bei den meisten Missionen) zurück; mit Universe-Speed skaliert.
- **Rückruf:** Eine laufende Flotte kann **zurückgerufen** werden (kehrt sofort um) — Basis
  für Fleetsave (§4).

---

## 3. Missionstypen

| Mission | Zweck |
|---------|-------|
| **Angriff** | feindlichen Planeten/Mond angreifen, plündern (→ Kampf, Doku 04) |
| **Transport** | Ressourcen zu eigenem/fremdem Planeten bringen |
| **Verlegen (Stationieren)** | Flotte dauerhaft auf eigenen Planeten verlegen |
| **Halten (Verteidigen)** | Flotte zeitweise bei einem Verbündeten stationieren |
| **Kolonisieren** | Kolonieschiff → freie Position (Astrophysik-Slot, Doku 02/06) |
| **Spionage** | Sonden zur Aufklärung (→ Doku 04 §6) |
| **Recycling** | Trümmerfeld mit Recyclern einsammeln (Doku 04 §3) |
| **Zerstören** | Superschiff vs. **Mond** (Mondzerstörung) |
| **Expedition** ⭐ | Erkundung des tiefen Raums (§5) |
| **ACS-Angriff / -Verteidigung** | koordinierter **Allianz-Kampfverband** (mehrere Spieler, synchron) → Doku 09 |

> **ACS (Allianz-Combat-System):** mehrere Spieler timen ihre Flotten auf dasselbe Ziel /
> denselben Verteidigungspunkt. Zentrales soziales Endgame-Feature (Detail Doku 09).

---

## 4. Fleetsave — Verteidigung durch Geschick ⭐-Entscheidung nötig

Im Genre überlebt man Angriffe, indem man die Flotte **nicht zuhause stehen lässt**:
man schickt sie auf einen langen Flug (z. B. Transport/Verlegen mit Drossel + Rückruf-Timing),
sodass sie zum Angriffszeitpunkt **unterwegs und unangreifbar** ist.

- *Pro:* tiefes, skillbasiertes Katz-und-Maus; Verluste sind selbst verschuldet.
- *Contra:* für Gelegenheitsspieler fummelig und „immer-online"-fördernd — Spannung mit
  unseren Casual-Bindungs-Zielen.

> ✅ **Entscheidung (2026-06-06): klassisches Flug-Fleetsave + zusätzliche Bunker-Option.**
> Das skillbasierte Flug-Fleetsave bleibt (Tiefe), ergänzt um einen zeitlich begrenzten
> **Bunker/Schutzhangar** (Kapazität + Cooldown) für Gelegenheitsspieler. Beste Balance aus
> Tiefe und Casual-Freundlichkeit.

---

## 5. Expeditionen ⭐

- Freigeschaltet über **Astrophysik** (Doku 02); eigene Slots; Ziel = **tiefer Raum** (Doku 06 §8).
- **Mögliche Ergebnisse** (prozedural, GDD §10.3; Texte LLM-vorgeneriert):
  Ressourcenfunde, seltene/verschollene Schiffe, **Commander-Bergung** (GDD §6.6),
  Anomalie-Lore, Händler-Begegnung — oder **Risiken** (Verluste, Verzögerung, Hinterhalt).
- **Commander-Kopplung:** Erkundungs-Spezialisten erhöhen Fund-Qualität (Fähigkeit
  *Anomalie-Analyse*, Doku 05); riskante Expeditionen sind eine Permadeath-Gefahr.

> ✅ **Entscheidung (2026-06-06): Expeditionen = Hauptsäule für *Funde*** (Forscher-Endgame:
> Commander-Bergung, seltene Schiffe, Lore, Ressourcen), **aber getrennt von der
> Kolonisierung.** Mehr Planeten besiedeln läuft ausschließlich über das **Astrophysik-Limit
> + freie Position wählen** (Doku 02/06) — Expeditionen schalten *keine* Kolonien frei.

---

## 6. ⭐ Commander auf Missionen

- Eine Flotte kann einem **Commander** unterstellt werden (Flaggschiff, Doku 03/04).
- **Einfluss:** Moral/Traits → Tempo- & Sprit-Effizienz (Logistik), Kampfausgang (Doku 04),
  Erfolgswahrscheinlichkeit/Qualität bei Expedition & Spionage.
- **Aktive Fähigkeiten** auf Missionen: *Eilmarsch* (Tempo↑), *Sparflug* (Sprit↓),
  *Störsender* (Gegen-Aufklärung) usw. (Doku 05 §6).
- **XP-Quelle:** erfolgreiche Missionen geben Commander-XP passend zur Spezialisierung.
- **Überdehnung:** sehr lange Dauer-Einsätze ohne Heimathafen-Erholung senken Moral
  (Doku 05 §4) → natürliche Grenze für Dauer-Raiding.

---

## 7. Tuning-Hebel & offene Entscheidungen 🔧

1. **Fleetsave-Modell:** ✅ **Entscheidung: klassisch + Bunker-Option** (§4).
2. **Stellenwert/Verdrahtung der Expeditionen:** ✅ **Entscheidung: Hauptsäule für Funde,
   getrennt von Kolonisierung** (§5). Kolonien rein über Astrophysik-Limit.
3. **Slot-Skalierung** (Computertechnik), Sprit-/Tempo-Formeln, Drossel-Stufen,
   Expeditions-Ergebnistabellen, Bunker-Kapazität/Cooldown, Rückruf-Regeln → Prototyp.

---

## 8. Abhängigkeiten zu anderen System-Dokus

- **03 Schiffe** — Tempo/Sprit/Fracht/Recycler/Kolonieschiff/Sonden.
- **04 Kampf** — Angriff, Spionage, Recycling von Trümmern, Flaggschiff.
- **06 Universum** — Distanzklassen, Kolonisierung, Monde (Sprungtor!), Deep Space.
- **02 Techbaum** — Computertechnik (Slots), Antriebe (Tempo), Astrophysik (Expeditionen).
- **09 Allianzen** — ACS-Missionen, Halten/Verteidigen.
- **GDD §6 / Doku 05** — Commander-Führung, Fähigkeiten, XP, Überdehnung.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Flottenmechanik (Slots/Tempo/Sprit/Rückruf),
  Missionstypen inkl. ACS, ⭐ Fleetsave-Fork, ⭐ Expeditionen, ⭐ Commander-auf-Missionen
  (Einfluss/Fähigkeiten/XP/Überdehnung), Tuning-Hebel.
