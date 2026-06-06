# System-Design: Schiffe & Einheiten

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · baut auf [01 Wirtschaft](./01-economy-and-buildings.md), [02 Techbaum](./02-technology-tree.md)
>
> Roster aller baubaren Einheiten: zivile Schiffe, Kampfschiffe, Verteidigung. Werte sind
> **relativ/Philosophie** (exakte Zahlen → Prototyp). Basis: OGame; ⭐ = Universe-spezifisch.

---

## 1. Designziele

1. **Stein-Schere-Papier mit Tiefe.** Keine „beste" Flotte — Zusammensetzung schlägt rohe
   Masse. Erreicht über **Schnellfeuer (Rapidfire)** statt simpler Konter.
2. **Kosten = Wert.** Hüllenpunkte leiten sich aus den Baukosten ab → teure Schiffe sind
   robuster, aber auch ein größeres Verlustrisiko (koppelt an Permadeath, GDD §6.7).
3. **Spielstil-Flotten.** Jeder Pfad (GDD §5) hat sinnvolle Kernschiffe.
4. **⭐ Crew statt nur Stahl.** Flotten werden von Commandern geführt; Moral verändert
   die effektiven Kampfwerte (GDD §6.2).

---

## 2. Werte-Grundlagen (gelten für alle Einheiten)

| Wert | Bedeutung |
|------|-----------|
| **Angriff** | Schaden pro Schuss. Skaliert mit **Waffentechnik** (+10 %/Stufe). |
| **Schild** | absorbiert Schaden. Schüsse < 1 % des Schilds **prallen ab**. Skaliert mit **Schildtechnik**. |
| **Hülle** | = (Metall + Kristall-Kosten) / 10, skaliert mit **Panzerung**. Unter ~30 % Hülle Explosionsrisiko. |
| **Schnellfeuer (Rapidfire)** | Chance, sofort erneut zu feuern, wenn Ziel ein bestimmter (meist schwächerer) Typ ist. **Der Kern der Tiefe.** |
| **Fracht** | Laderaum (Beute/Transport). |
| **Tempo** | Grundgeschwindigkeit, abhängig vom Antrieb (Verbrennung/Impuls/Hyperraum). |
| **Sprit** | Deuterium-Verbrauch pro Flug (Distanz × Verbrauch). |

> ⭐ **Moral-Modifikator:** Effektiver Angriff & Schild der Flotte = Basiswert ×
> `(1 + Moralbonus)` des führenden Commanders (Bereich z. B. −25 % … +10 %, GDD §6.2).

---

## 3. Zivile Schiffe

| Einheit | Rolle | Frachthinweis | Voraussetzung (Tech) |
|--------|-------|---------------|----------------------|
| **Kleiner Transporter** | schneller Beute-/Versorgungstransport | klein | Verbrennung |
| **Großer Transporter** | Massentransport, Raid-Beute abtransportieren | groß | Verbrennung |
| **Kolonieschiff** | gründet neue Kolonien (mit Astrophysik-Slot, §02) | — | Impulstriebwerk |
| **Recycler** | sammelt **Trümmerfelder** nach Schlachten ein | mittel | Verbrennung + Schild |
| **Spionagesonde** | Aufklärung gegnerischer Planeten | winzig | Spionagetechnik |
| **Solarsatellit** | liefert Energie im Orbit (kein Antrieb, **im Kampf zerstörbar**) | — | — |

> Trümmerfelder (zerstörte Schiffe → Metall/Kristall im Orbit) sind ein zentrales
> Wirtschafts-/Kampf-Bindeglied → Recycler-Gameplay, Details Doku 04 Kampf.

---

## 4. Kampfschiffe (relative Einordnung)

Skala: ⭐ niedrig → ⭐⭐⭐⭐⭐ hoch. „RF vs." = profitiert von Schnellfeuer gegen.

| Schiff | Angriff | Hülle | Tempo | RF stark vs. | Rolle | Tech-Gate |
|--------|:---:|:---:|:---:|--------------|-------|-----------|
| **Leichter Jäger** | ⭐ | ⭐ | ⭐⭐⭐⭐ | — | Masse-Kanonenfutter, billig | Verbrennung |
| **Schwerer Jäger** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | kleine Transporter, Sonden | besserer Jäger | Impuls + Panzerung |
| **Kreuzer** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | leichte Jäger, Raketenwerfer | Allrounder, Jäger-Killer | Impuls + Ion |
| **Schlachtschiff** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | — | Rückgrat großer Flotten | Hyperraumantrieb |
| **Schlachtkreuzer** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | Kreuzer, Schlachtschiffe, Transporter | Flotten-Jäger | Hyperraumtechnik + Laser |
| **Bomber** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | **Verteidigung** | Verteidigungs-Brecher | Impuls + Plasma |
| **Zerstörer** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | leichte Lasergeschütze, Schlachtkreuzer | schwere Artillerie | Hyperraumantrieb + Plasma |
| **Todesstern** ⭐ (Superschiff) | ⭐⭐⭐⭐⭐+ | ⭐⭐⭐⭐⭐+ | ⭐ (sehr langsam) | fast alles | Endgame-Belagerung; siehe §6 | Gravitontechnik |

---

## 5. Verteidigung (planetar, fliegt nicht)

Verteidigung ist billiger als Schiffe pro Kampfwert, aber ortsgebunden. Ein Teil der
zerstörten Verteidigung **regeneriert** nach dem Kampf (🔧 Prozent).

| Verteidigung | Rolle |
|--------------|-------|
| **Raketenwerfer** | billiges Kanonenfutter, Masse |
| **Leichtes / Schweres Lasergeschütz** | solide Allround-Verteidigung |
| **Gaußkanone** | hoher Einzelschaden, gegen große Schiffe |
| **Ionengeschütz** | hoher Schild, hält viel aus |
| **Plasmawerfer** | stärkste Verteidigung |
| **Kleine / Große Schildkuppel** | je 1 pro Planet, absorbiert massiv |
| **Abfangrakete / Interplanetarrakete** | fängt feindliche Raketen ab / zerstört feindliche Verteidigung |

---

## 6. ⭐ Commander-Kopplung & Flaggschiff (Universe-spezifisch)

Hier verschmilzt der Roster mit dem USP:

- **Flottenführung:** Jede ausfliegende Flotte kann einem **Commander** unterstellt werden.
  Dessen Moral & Traits modifizieren Kampfwerte (§2), Tempo-/Spritboni (Logistik-Traits)
  und das Verhalten (vorsichtige Commander ziehen sich früher zurück).
- **Flaggschiff-Konzept (Vorschlag):** Der Commander reist auf einem designierten
  Flaggschiff. **Geht das Flaggschiff unter und die Flotte wird vernichtet → greift die
  Permadeath-/Capture-Logik** (GDD §6.7). Das macht Kampf emotional und riskant, statt nur
  Zahlenvergleich — und liefert die dramatischsten LLM-Funkspruch-Momente.
- **Span-of-Control im Feld:** Wie viele Geschwader ein Commander *effektiv* führt, begrenzt
  über Span (GDD §6.4) den Nutzen riesiger Einzelflotten → organische Veteranen-Bremse.

> **Superschiff (Todesstern): Entscheidung nötig.** Ikonisch, aber Quelle von Late-Game-
> Runaway (ein Veteran mit Todessternen ist fast unangreifbar). Optionen in §8.

---

## 7. Spielstil-Flotten (Richtwerte)

| Spielstil | Kernschiffe |
|-----------|-------------|
| **Forscher/Erkunder** | Spionagesonden, Kolonieschiffe, schnelle Späher, Pathfinder-artige Erkunder |
| **Militär/Piraterie** | Schlachtkreuzer, Kreuzer, Zerstörer, Bomber, große Transporter (Beute) |
| **Wirtschaft/Handel** | große Transporter, Recycler, Solarsatelliten, schlanke Eskorte |

---

## 8. Tuning-Hebel & offene Entscheidungen 🔧

1. **Superschiff (Todesstern):** ✅ **Entscheidung (2026-06-06): Ja, hart gegatet** —
   nur via Gravitontechnik, enorme Kosten, sehr langsam. Endgame-Ziel, aber als
   verwundbare Investition statt Selbstläufer.
2. **Flaggschiff/Permadeath-Kopplung:** ✅ **Entscheidung (2026-06-06): koppeln** —
   Commander reist auf Flaggschiff; Vernichtung mit der Flotte löst Permadeath/Capture aus
   (GDD §6.7). Maximales Drama & klare Risiko-Entscheidung.
3. **Rapidfire-System** — volle OGame-Tiefe (geliebt, komplex) beibehalten (empfohlen) vs.
   simpleres Konter-System. → in Doku 04 final.
4. **Verteidigungs-Regeneration %** nach Kampf — Prototyp.
5. **Exakte Werte/Kosten/Sprit/RF-Tabellen** — Prototyp + Balance-Tool.

---

## 9. Abhängigkeiten zu anderen System-Dokus

- **01 Wirtschaft** — Werft-Bauzeit, Kosten, Hülle = Kosten/10, Solarsatellit = Energie.
- **02 Techbaum** — Tech-Gates, Waffen/Schild/Panzerung-Boni.
- **04 Kampf** — Rapidfire, Schild-Abprall, Trümmerfelder, Flaggschiff/Permadeath.
- **07 Flottenmissionen** — Tempo, Sprit, Fracht, Recycler/Kolonie/Spionage-Missionen.
- **GDD §6 Commander** — Flottenführung, Moral-Modifikator, Flaggschiff, Span.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Werte-Grundlagen (inkl. Rapidfire & Moral-Modifikator),
  ziviler + Kampf-Roster, Verteidigung, ⭐ Flaggschiff/Commander-Kopplung, Spielstil-Flotten,
  Tuning-Hebel (Superschiff, Flaggschiff-Permadeath, Rapidfire).
