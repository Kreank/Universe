# System-Design: Wirtschaft & Gebäude

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · Schwester-Doku: [Architektur](../ARCHITECTURE.md)
>
> Das Zahlen-Fundament. Alle anderen Systeme (Schiffskosten, Kampf, Pacing) bauen
> hierauf auf. Basis sind die bewährten OGame-Formeln; **unsere Abweichungen sind klar
> markiert** (🔧 = Tuning-Hebel, ⭐ = Universe-spezifisch, neu).

---

## 1. Designziele dieses Systems

1. **Der „immer mehr"-Loop.** Kosten steigen exponentiell *schneller* als Produktion →
   man braucht permanent mehr Planeten/Effizienz. Das ist der Kern-Antrieb.
2. **Sinnvolle Entscheidungen statt Auto-Pilot.** Welche Mine als Nächstes? Energie
   decken oder Risiko? Lager bauen oder ausgeben? Jede Stufe ist eine Abwägung.
3. **Lesbar trotz Tiefe.** Formeln sind transparent (Spieler können planen), nicht versteckt.
4. **Kein Pay-to-Win in der Wirtschaft.** Premium darf Komfort/Zeit geben, nie rohe Macht
   (Details → System-Doku 12 Fairness).

---

## 2. Ressourcenmodell

| Ressource | Lagerbar | Rolle |
|-----------|:---:|-------|
| **Metall** | ✅ | Hauptbaustoff (Gebäude, Schiffe, Verteidigung) — am häufigsten |
| **Kristall** | ✅ | Elektronik, höherwertige Schiffe, Forschung — wertvoller als Metall |
| **Deuterium** | ✅ | Treibstoff (Flüge), Forschung, Fusions-Energie — knappste Ressource |
| **Energie** | ❌ | **Bilanz**, kein Vorrat. Deckt den Verbrauch der Minen. Defizit drosselt Produktion. |

**Relativer Wert (Handels-Richtwert, 🔧):** 3 Metall : 2 Kristall : 1 Deuterium.
Diese Ratio steuert späteren Handel & Markt.

> ⭐ **Keine vierte Kern-Ressource.** Eine evtl. Premium-/Spezialwährung (z. B. „Dunkle
> Materie" für Komfort) ist *kein* Wirtschafts-Rohstoff und wird in Doku 12 behandelt.

---

## 3. Produktionsformeln (Basis, Universe-Speed ×1)

Produktion **pro Stunde**, `lvl` = Gebäudestufe:

```
Metall-Mine:          30 × lvl × 1,1^lvl
Kristall-Mine:        20 × lvl × 1,1^lvl
Deuterium-Synth.:     10 × lvl × 1,1^lvl × (1,36 − 0,004 × T_max)
Grundeinkommen:       +30 Metall/h, +15 Kristall/h  (Stufe 0, immer)
```

- **T_max** = Maximaltemperatur des Planeten (°). Heiße Planeten → **weniger** Deuterium,
  kalte → mehr (→ Planetentypen, System-Doku 6).
- Alle Werte werden mit dem **Universe-Speed** multipliziert (🔧 §9).

⭐ **Commander-Kopplung:** Ein der **Wirtschaft** zugewiesener Commander gibt
`+Bonus% × (Moral/100)` auf die Produktion seines Planeten (Bonus je nach Rang/Traits,
Default-Spitze ~+10 %). Verknüpft das Wirtschafts- mit dem Commander-System (GDD §6).

---

## 4. Energiemodell

Energie wird **nicht gelagert** — es zählt die Bilanz `Produktion − Verbrauch`.

**Verbrauch pro Stunde:**
```
Metall-Mine:        10 × lvl × 1,1^lvl
Kristall-Mine:      10 × lvl × 1,1^lvl
Deuterium-Synth.:   20 × lvl × 1,1^lvl
```

**Erzeugung:**
```
Solarkraftwerk:     20 × lvl × 1,1^lvl
Fusionsreaktor:     30 × lvl × (1,05 + 0,01 × EnergieTech)^lvl   (verbraucht Deuterium)
Solar-Satellit:     (T_max + 160) / 6   pro Satellit   (im Orbit, zerstörbar im Kampf)
```

**Defizit-Regel:** Reicht die Energie nicht, läuft die Minen-Produktion nur mit
`Faktor = verfügbare Energie / benötigte Energie` (0–1). → Energie ist ein **harter
Drossel-Mechanismus**, kein optionaler Bonus. Energie-Management ist Pflicht-Gameplay.

> **Trade-off Fusion vs. Solar:** Solar ist „gratis" laufende Energie, skaliert aber
> teuer. Fusion liefert viel Energie, frisst aber Deuterium (das du auch als Sprit
> brauchst). Solar-Satelliten sind billig/effektiv, aber im Kampf zerstörbar → Risiko.

---

## 5. Baukosten & Skalierung

Kosten einer Stufe: `Basis × Faktor^(lvl−1)`. Die Differenz zur Vorstufe ist der Preis
des nächsten Ausbaus. **Faktoren < 1,1^... bei der Produktion ⇒ Kosten wachsen schneller
als Ertrag** — das erzeugt absichtlich den Druck zu expandieren.

| Gebäude | Basiskosten (M / K / D) | Faktor | Effekt |
|---------|--------------------------|:---:|--------|
| Metall-Mine | 60 / 15 / 0 | ×1,5 | +Metallproduktion |
| Kristall-Mine | 48 / 24 / 0 | ×1,6 | +Kristallproduktion |
| Deuterium-Synth. | 225 / 75 / 0 | ×1,5 | +Deuteriumproduktion |
| Solarkraftwerk | 75 / 30 / 0 | ×1,5 | +Energie |
| Fusionsreaktor | 900 / 360 / 180 | ×1,8 | +Energie (−Deut) |
| Roboterfabrik | 400 / 120 / 200 | ×2,0 | schnellere Bauzeit |
| Naniten-Fabrik | 1.000.000 / 500.000 / 100.000 | ×2,0 | stark schnellere Bauzeit |
| Raumschiffwerft | 400 / 200 / 100 | ×2,0 | baut Schiffe & Verteidigung |
| Forschungslabor | 200 / 400 / 200 | ×2,0 | ermöglicht/beschleunigt Forschung |
| Metallspeicher | 1.000 / 0 / 0 | ×2,0 | +Lagerkapazität Metall |
| Kristallspeicher | 1.000 / 500 / 0 | ×2,0 | +Lagerkapazität Kristall |
| Deuteriumtank | 1.000 / 1.000 / 0 | ×2,0 | +Lagerkapazität Deuterium |
| ⭐ **Kommando-Akademie** | 1.000 / 1.000 / 500 | ×2,0 | bildet Commander aus (§7.1) |
| ⭐ **Kommandozentrale** | 5.000 / 3.000 / 1.000 | ×2,0 | erhöht Span-of-Control (§7.2) |

> 🔧 Alle Basiskosten/Faktoren sind tunebar. Höherer Faktor = mehr Grind/Expansion-Druck;
> niedrigerer = flacheres, zugänglicheres Spiel (§9).

---

## 6. Lager & Bauzeit

**Lagerkapazität** (je Speicherstufe):
```
Kapazität = 5000 × floor( 2,5 × e^(20 × lvl / 33) )
```
Überlauf wird **nicht** gespeichert → geht verloren. Anreiz, zu investieren statt zu horten
(verstärkt durch Decay, §8).

**Bauzeit (Gebäude), in Stunden:**
```
Zeit = (Metall + Kristall) / (2500 × (1 + Roboterfabrik-Lvl) × 2^Naniten-Lvl × Speed)
```
- Roboterfabrik & Naniten-Fabrik sind die zwei Hebel gegen Wartezeit.
- Schiffe/Verteidigung: analog, aber durch die **Raumschiffwerft-Stufe** beschleunigt
  (Details → System-Doku 3 Schiffe).

---

## 7. Universe-spezifische Gebäude ⭐

### 7.1 Kommando-Akademie
Der Grundpfad der Commander-Beschaffung (GDD §6.6). Höhere Stufe ⇒
- schnellere Ausbildung,
- höherer Start-Rang der Kadetten,
- mehr **gleichzeitige** Ausbildungsplätze.

> Offen (Tuning): Ausbildungszeit-Kurve, Rang-Schwellen je Stufe. → Prototyp.

### 7.2 Kommandozentrale
Erhöht die **Span-of-Control** des Spielers/Admirals (GDD §6.4): Default 3 direkt
unterstellte Commander, +1 je Stufe mit **abnehmendem** Ertrag (z. B. +1, +1, dann
steigende Kosten/halbe Schritte), damit Veteranen keine unbegrenzte Befehlskette stapeln.

> Diese beiden Gebäude sind der wirtschaftliche „Einstieg" ins Commander-System — sie
> verbinden Doku 01 direkt mit dem USP.

---

## 8. Persistenz: Decay & Inaktivität ⭐

Da es **keine Universum-Resets** gibt (GDD §7), bremst Decay tote Wirtschaft aus:

- **Inaktivität** (kein Login über Schwelle X): Produktion sinkt schrittweise; nach
  längerer Zeit verlieren Gebäude langsam effektive Stufen / Kolonien werden aufgebbar.
- Zweck: Karte & Wirtschaft gesund halten, ohne harten Reset.
- 🔧 Schwellen & Rate → Prototyp; muss mit Neulingsschutz (GDD §8) und Saison-Rhythmus
  (GDD §7.3) abgestimmt sein, damit normale Pausen (Urlaub!) **nicht** bestraft werden.
  → Urlaubsmodus vorsehen (pausiert Produktion *und* Angreifbarkeit *und* Decay).

---

## 9. Tuning-Hebel & offene Balance-Entscheidungen 🔧

Die folgenden Stellschrauben verändern das gesamte Spielgefühl.

1. **Universe-Speed** — globaler Multiplikator auf Produktion *und* Flottentempo.
   ✅ **Entscheidung (2026-06-06): ×5–×10 (modern/zugänglich).** Fortschritt in Stunden
   statt Tagen; passt zu unseren Casual-Bindungs- und Anti-Bashing-Zielen. Exakter Wert
   im Korridor 5–10 → Prototyp.
2. **Kurven-Steilheit** — Kosten-/Produktionsfaktoren.
   ✅ **Entscheidung (2026-06-06): vorerst OGame-nah belassen, Steilheit im Prototyp am
   echten Spielgefühl tunen.** Tendenz: eher etwas flacher, falls Late-Game zu explosiv
   wird (unterstützt Anti-Bashing, GDD §8).
3. **Offline-Produktion** — ✅ volle Produktion offline (Kern des Genres, idle-freundlich).
4. **Energie als harte Drossel** — ✅ beibehalten (Pflicht-Gameplay).

---

## 10. Beispiel: ROI-Denkweise (für spätere Balance-Tools)

Eine Mine lohnt sich, wenn ihre **Mehrproduktion** die **Ausbaukosten** in akzeptabler Zeit
zurückzahlt. Da Kosten (×1,5/1,6) schneller steigen als Ertrag (×1,1), wird jede Stufe
*relativ* teurer → der natürliche Punkt, an dem Expansion (neue Kolonie) attraktiver wird
als weiteres Hochziehen einer Mine. Genau dieser Kipppunkt ist die zentrale
Pacing-Schraube und wird mit einem kleinen ROI-Rechner im Prototyp validiert.

---

## 11. Abhängigkeiten zu anderen System-Dokus

- **03 Schiffe** — Bauzeit/Kosten nutzen Werft & dieselbe Kostenlogik.
- **02 Technologiebaum** — Forschungen modifizieren Produktion/Energie (z. B. EnergieTech,
  Plasmatechnik) und schalten Gebäude frei.
- **04 Kampf** — zerstörte Solar-Satelliten/Gebäude, Plünderung greifen hier an.
- **06 Universum** — Planetentyp/Temperatur ⇒ Deuterium & Energie.
- **GDD §6 Commander** — Akademie, Kommandozentrale, Produktions-Bonus durch Moral.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Ressourcenmodell, Produktions-/Energie-/Kostenformeln
  (OGame-Basis), Lager/Bauzeit, eigene Gebäude (Akademie, Kommandozentrale), Decay,
  Tuning-Hebel, ROI-Denkweise.
