# System-Design: Kampfmodell

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · baut auf [03 Schiffe](./03-ships-and-units.md), koppelt eng an **GDD §6 Commander**
>
> Wie Schlachten ablaufen — und wie Commander, Moral, Flaggschiff und Permadeath darin
> verschmelzen. Das ist der Punkt, an dem sich *Universe* am stärksten von OGame absetzt.
> Basis: bewährte OGame-Kampfmechanik; ⭐ = Universe-spezifisch.

---

## 1. Designziele

1. **Komposition schlägt Masse.** Über Schnellfeuer (Rapidfire) gewinnt die *klügere*
   Flotte, nicht nur die größere.
2. **Kampf ist eine Entscheidung, kein Zufall.** Aufklärung, Flottenmix, Commander-Wahl
   und Timing bestimmen den Ausgang; RNG ist nur Würze.
3. **⭐ Emotionaler Einsatz.** Durch Flaggschiff/Permadeath steht bei jeder großen Schlacht
   etwas Unwiederbringliches auf dem Spiel → Spannung statt reinem Zahlenvergleich.
4. **Reproduzierbar & fair.** Jeder Kampf erzeugt einen nachvollziehbaren Bericht (Seed),
   den ein Simulator vorab nachstellen kann.

---

## 2. Ablauf einer Schlacht

Eine Schlacht wird beim Eintreffen der Flotte **sofort serverseitig berechnet** (autoritativ,
Architektur §5.3) und läuft über **bis zu 8 Runden** (`combat.max_rounds`):

1. **Pro Runde** feuert jede Einheit auf ein **zufälliges** gegnerisches Ziel.
2. **Schaden** trifft zuerst den **Schild**, Rest geht auf die **Hülle**.
3. **Schild-Abprall:** Ein Schuss, dessen Schaden **< 1 % des Ziel-Schilds** ist, prallt
   wirkungslos ab → kleine Schiffe können große kaum kratzen (Klassen-Relevanz).
4. **Schnellfeuer (Rapidfire):** Trifft eine Einheit einen Typ, gegen den sie RF hat, darf
   sie mit Wahrscheinlichkeit `(RF−1)/RF` **sofort erneut** feuern (kettenbar). → der
   eigentliche taktische Kern.
5. **Rundenende:** Schilde **regenerieren** auf voll; Hüllenschäden **bleiben**. Einheiten
   unter ~70 % Hülle haben eine **Explosionschance** = `1 − (Resthülle / Maxhülle)`.
6. Schlacht endet nach Runde 6 **oder** wenn eine Seite vernichtet ist.

> Verteidigung (planetar) kämpft mit; ein Teil **regeneriert** nach der Schlacht (🔧 %).

---

## 3. Nach der Schlacht: Trümmer, Beute, Verteidigung

- **Trümmerfeld:** Ein Anteil (🔧, Default ~30 %) der **zerstörten Schiffe** (Metall +
  Kristall) bleibt als Trümmerfeld im Orbit und ist mit **Recyclern** einsammelbar →
  zentrales Wirtschafts-/Konflikt-Bindeglied.
- **Plünderung:** Der Sieger plündert bis zu **50 %** der ungeschützten Rohstoffe des
  Ziels, begrenzt durch **Frachtraum** der mitgeführten Schiffe.
  - ⭐ Unter **Neulingsschutz** (GDD §8) ist die Plünderquote stark reduziert/0 und es
    entsteht **kein** Permadeath/Capture.
- **Verteidigungs-Regeneration:** Ein Teil der zerstörten Verteidigung wird nach dem Kampf
  wiederhergestellt (🔧) — macht Planeten-Verteidigung langfristig lohnend.

---

## 4. ⭐ Commander & Moral im Kampf (USP)

Vor und nach der Schlacht greift das Commander-System (GDD §6):

**Vor der Schlacht — Modifikatoren:**
- **Moral-Multiplikator** auf effektiven **Angriff & Schild** der geführten Flotte
  (Bereich z. B. −25 % … +10 %, GDD §6.2).
- **Trait-Effekte** (siehe Tiefe in §6 / Doku 05):
  - *aggressiv:* +Angriff, −Defensive/höheres Eigenrisiko
  - *vorsichtig:* zieht sich früher zurück, geringere eigene Verluste, evtl. weniger Beute
  - *logistisch:* bessere Sprit-/Tempo-Effizienz, schnellere Moral-Erholung danach
- **Span-of-Control:** Übersteigt die Flotte die effektive Führungskapazität des Commanders,
  greifen Koordinationsstrafen (Teil der Flotte feuert verspätet/ineffektiv) → Veteranen-Bremse.

**Nach der Schlacht — Konsequenzen:**
- **Moral-Verschiebung:** Sieg hebt, Niederlage senkt Moral; deutliche Über-/Unterlegenheit
  verstärkt den Effekt (sinnloses Bashing senkt Moral, GDD §8).
- **Reaktions-Funkspruch:** sofortiger Bank-Lookup + Slot-Filling (Architektur §5.3, GDD
  §10.5) — der Commander „meldet" das Ergebnis in Echtzeit. Großmomente bekommen einen
  per-LLM nachgereichten Bericht (Architektur §5.4).

---

## 5. ⭐ Flaggschiff, Permadeath & Capture-Auflösung

Der dramatischste Mechanismus. Tritt **nur** bei Verlust der vom Commander geführten Flotte ein:

```
Flotte des Commanders im Kampf vernichtet?
        │ nein → Commander unversehrt, normale Moral-Folgen
        ▼ ja
Evakuierungs-/Entkommens-Wurf  (Leitplanke gegen Willkür)
   Chance erhöht durch: überlebende eigene Schiffe, Logistik-Tech/-Traits, hoher Rang
        │ erfolgreich → Commander entkommt (verwundet: Auszeit + Moral-Malus)
        ▼ gescheitert
Sieger nimmt Commander gefangen?  (Militär-Pfad-Mechanik, GDD §6.6)
        │ ja → Gefangenschaft: Lösegeld / Rettungsmission / Abwerben (Loyalitätsrisiko)
        ▼ nein (oder Extremfall: totale Vernichtung)
PERMADEATH  →  Commander endgültig verloren; großer Trauer-/Crew-Moral-Effekt,
               LLM-würdiges Ereignis („Wir haben Admiral X verloren")
```

- **Progressiver Schutz:** Höherrangige Commander haben bessere Entkommens-Chancen und sind
  schwerer permanent zu verlieren (GDD §6.7).
- **Neulingsschutz:** unter Schutz **kein** Permadeath/keine permanente Gefangennahme (§3).

> Diese Kette ist der Grund, warum große Angriffe sich *gefährlich* anfühlen — du riskierst
> nicht nur Schiffe (ersetzbar), sondern eine über Wochen aufgebaute Persönlichkeit.

---

## 6. Aufklärung & Vorbereitung

- **Spionage zuerst:** Mit **Spionagesonden** (Tech: Spionagetechnik) sieht der Angreifer
  vorab Flotte, Verteidigung und Rohstoffe — abhängig vom Spionagetech-Vorsprung; das Ziel
  bemerkt die Sonden ggf. (Gegen-Spionage). Blindangriffe sind riskant.
- **Kampf-Simulator (Feature):** In-Game-Simulator, der einen Kampf mit gegebenen Flotten
  deterministisch (Seed) durchrechnet → Spieler planen statt zu raten. Nutzt dieselbe
  Engine wie der echte Kampf (eine Wahrheit, kein Drift).

---

## 7. Technische Anbindung

- Kampf wird **synchron im Game-Server** (Modul `combat`) bei Flottenankunft berechnet
  (Architektur §4) und als **`combat_reports`** persistiert (Architektur §7).
- `combat` erzeugt **Reaktions-Events** → `messaging` (Sofort-Funkspruch) und enqueued
  optional einen **Großmoment-Job** an den AI-Worker (Architektur §5.3/§5.4).
- Permadeath/Capture aktualisiert `commanders.status` und ggf. `commander_links`.

---

## 8. Tuning-Hebel & offene Entscheidungen 🔧

1. **Tiefe der Commander-Taktik:** ✅ **Entscheidung (2026-06-06): aktive Fähigkeiten** —
   einsetzbare Manöver (Konzentriertes Feuer, Rückzug, Flanke …) zusätzlich zu Moral-/
   Trait-Modifikatoren. Umsetzung: für den Vertical Slice ggf. mit Modifikatoren starten,
   aktive Fähigkeiten zügig nachziehen. Details → Doku 05.
2. **Evakuierungs-Regel:** ✅ **Entscheidung (2026-06-06): Entkommen nur, wenn eigene
   Schiffe überleben** (Logistik-Tech/Rang erhöhen die Chance). Totale Vernichtung = echtes
   Permadeath-Risiko.
3. **Rundenzahl** (Default 8), **Trümmer-%** (Default 30, Schiffe; Verteidigung erzeugt
   Trümmer? Default nein), **Plünderquote** (Default 50 %), **Verteidigungs-Regen %** —
   alles Prototyp-Tuning.
4. **Rapidfire** — volle OGame-Tiefe beibehalten (empfohlen).
5. **Mond-/Sonderfolgen großer Trümmerfelder** — optional, späteres Feature.

---

## 9. Abhängigkeiten zu anderen System-Dokus

- **03 Schiffe** — Werte, Rapidfire, Flaggschiff, Verteidigung.
- **02 Techbaum** — Waffen/Schild/Panzerung, Spionage.
- **07 Flottenmissionen** — Anflug, Recycler (Trümmer), Rückzug, Sprit.
- **GDD §6 / Doku 05 Commander** — Moral, Traits, Span, Permadeath/Capture, Flaggschiff.
- **GDD §8 / §10** — Neulingsschutz, Reaktions-Funksprüche.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Rundenablauf (Rapidfire, Schild-Abprall, Explosion),
  Trümmer/Beute/Verteidigung, ⭐ Commander-&-Moral-Integration, ⭐ Flaggschiff-/Permadeath-/
  Capture-Auflösung, Aufklärung & Simulator, technische Anbindung, Tuning-Hebel.
