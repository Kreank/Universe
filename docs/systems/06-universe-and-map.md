# System-Design: Universum & Karte

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · trägt das „kein Reset"-Konzept (GDD §7) · koppelt an [02 Techbaum](./02-technology-tree.md), [07 Missionen]
>
> Struktur der Spielwelt, Planeten, Reisen — und die **Frontier-Mechanik**, das Herzstück
> des persistenten Universums. Basis: OGame-Koordinaten; ⭐ = Universe-spezifisch.

---

## 1. Designziele

1. **Persistenz ohne Verstopfung** (GDD-Säule 3). Die Karte bleibt erhalten, fühlt sich aber
   nie „voll" oder „tot" an — über Frontier-Expansion (§6) und Decay (§7).
2. **Position als Entscheidung.** Wo du siedelst, hat Konsequenzen (Ressourcen, Sicherheit,
   Nachbarn, Reichweite).
3. **Reichweite strukturiert Konflikt.** Distanz/Sprit machen Nähe wertvoll → Allianzen
   bilden Territorien, Bashing über die halbe Galaxie ist teuer.

---

## 2. Koordinaten-Struktur

Klassische, bewährte Hierarchie — adressierbar als **[Galaxie : System : Position]**:

```
Universum
└── Galaxien            (wächst dynamisch, §6)
    └── Sonnensysteme   (z. B. 1–499 je Galaxie)
        └── Positionen  (z. B. 1–15 Planetenplätze je System)
            └── Planet (+ optionaler Mond, §4)
```

- **[G:S:P]** ist die Adresse für Spionage, Angriff, Kolonisierung, Handel.
- Galaxie-/Systemansicht ist der zentrale „Karten"-Screen (Nachbarn sehen, Ziele wählen).

---

## 3. Planeten: Typ, Temperatur, Größe

Die **Position im System** bestimmt die Planeten-Eigenschaften (innere = heiß/eher klein,
äußere = kalt/eher groß — mit Streuung):

- **Temperatur** steuert (Doku 01): **heiß → weniger Deuterium, aber mehr Solar-Satelliten-
  Energie**; **kalt → mehr Deuterium, weniger Sat-Energie.** ⇒ echter Standort-Trade-off.
- **Größe (Felder):** begrenzt die Zahl gleichzeitiger Gebäude → große Planeten sind
  begehrt; Ausbau via späterer Tech/Gebäude (Terraformer o. Ä., später).
- **Heimatplanet:** garantiert solide Startwerte (fairer Einstieg).

> 🔧 Verteilungs-Tabellen (Temperatur/Felder je Position) → Prototyp.

---

## 4. Monde ⭐ (strategische Ebene)

Monde entstehen mit einer Chance aus **großen Trümmerfeldern** nach Schlachten (Doku 04) —
ein Anreiz, große Kämpfe zu suchen.

- **Bauplatz:** zusätzliche (begrenzte) Felder für Spezialgebäude.
- **Sensor-Phalanx:** scannt feindliche **Flottenbewegungen** in Reichweite → Aufklärung
  & Verteidigungs-Vorwarnung.
- **Sprungtor:** teleportiert eigene Flotten zwischen Monden (mit Cooldown) → verkürzt die
  durch Distanz erzwungene Reichweite gezielt; mächtiger Allianz-Logistik-Hebel.

> Monde sind optional, aber empfohlen — sie geben dem Kampf eine bleibende, territoriale
> Konsequenz. (Default: aufnehmen.)

---

## 5. Kolonisierung & Reise

- **Kolonisierung:** Kolonieschiff zu einer **freien Position** schicken; Anzahl der
  Kolonien gegated über **Astrophysik** (Doku 02 §5). Planetenqualität = Funktion der
  Zielposition (Zufall im Rahmen).
- **Distanzklassen** (steuern Flugzeit & Sprit, mit Universe-Speed skaliert):
  1. innerhalb desselben **Systems** — schnell/billig
  2. andere Systeme derselben **Galaxie** — mittel
  3. andere **Galaxie** — langsam/teuer
- Folge: **Nähe ist wertvoll.** Allianzen bilden zusammenhängende Territorien; Angriffe auf
  weit entfernte (schwächere) Ziele sind unattraktiv → unterstützt Anti-Bashing (GDD §8).

---

## 6. ⭐ Frontier-Expansion & Regionen-Modell (Kern des persistenten Universums)

Statt das Universum zu resetten, **wächst** es und ist in **Ringe** gegliedert:

```
   [ KERN ]      ← älteste, reichste, am stärksten umkämpfte Galaxien (Veteranen)
  [  MITTE  ]    ← etablierter Raum, gemischt
 [  FRONTIER  ]  ← neueste Galaxien: hier spawnen NEUE Spieler (geschützt), NPC-reich
```

- **Neue Spieler spawnen an der Frontier** — räumlich getrennt von Veteranen (GDD §8).
- **Frontier-Expansion:** Füllt sich die äußerste Region, öffnet das System **neue
  Galaxien** → es gibt immer frischen Raum, ohne Reset.
- **Regions-Regeln (Vorschlag):** Frontier = stärkerer Neulingsschutz, mehr PvE/NPC-Gehalt;
  Kern = höhere Belohnungen/Dichte, härterer PvP. So „wandert" man mit dem eigenen Aufstieg
  nach innen.
- **NPC-Imperien** (Doku 08) besiedeln Frontier/Leerräume, damit nichts tot wirkt.

> 🔧 Forks: (a) **Regionen-Modell** wie oben vs. flache Karte ohne Ringe; (b) **Auslöser**
> der Expansion: bevölkerungs-/dichtebasiert vs. zeitbasiert. → §9.

---

## 7. Decay & Karten-Hygiene ⭐

Da nie resettet wird, hält Decay (GDD §7.2, Doku 01 §8) die Karte gesund:

- Inaktive Planeten degradieren; nach langer Inaktivität werden sie **aufgebbar/
  kolonisierbar** oder zerfallen zu Trümmern → frei werdende Positionen für aktive Spieler.
- **Urlaubsmodus** schützt davor (pausiert Produktion, Angreifbarkeit *und* Decay) —
  normale Pausen werden nicht bestraft.

---

## 8. Deep Space & Expeditionen ⭐

- Jenseits der regulären Positionen existiert **tiefer Raum** (vgl. „Position 16"/
  Expeditionsslot): Ziel für **Expeditionen** (freigeschaltet via Astrophysik, Doku 02).
- Expeditionen liefern Ressourcen, Funde, seltene Schiffe, **Commander-Bergung** (GDD §6.6)
  oder Risiken (Verluste) — prozedural generierte Ereignisse (GDD §10.3), Texte LLM-vorgeneriert.
- Details der Missions-Mechanik → Doku 07.

---

## 9. Tuning-Hebel & offene Entscheidungen 🔧

1. **Regionen-Modell:** ✅ **Entscheidung (2026-06-06): konzentrische Ringe**
   (Kern/Mitte/Frontier) mit eigenen Regeln. Man wandert mit dem Aufstieg nach innen;
   trägt Anti-Bashing & Frontier-Konzept.
2. **Frontier-Expansions-Auslöser:** ✅ **Entscheidung (2026-06-06): bevölkerungs-/
   dichtebasiert** — neue Galaxie öffnet bei Füllung der äußersten Region. Karte bleibt
   immer angenehm besiedelt.
3. **Monde aufnehmen** — Default: ja (Phalanx/Sprungtor geben Kampf territoriale Tiefe).
4. **Galaxie-/System-/Positions-Dimensionen**, Distanz-/Sprit-Formeln, Temperatur-/Feld-
   Verteilungen, Mond-Chance → Prototyp.

---

## 10. Abhängigkeiten zu anderen System-Dokus

- **01 Wirtschaft** — Temperatur → Deuterium/Energie; Felder → Bauplätze.
- **02 Techbaum** — Astrophysik (Kolonien/Expeditionen), Antriebe (Reichweite).
- **04 Kampf** — Trümmerfelder → Monde; Phalanx → Aufklärung.
- **07 Missionen** — Reise/Sprit, Kolonisieren, Expeditionen, Recycling.
- **08 NPC-Imperien** — Besiedlung von Frontier/Leerraum.
- **GDD §7/§8** — kein Reset, Frontier-Trennung, Neulingsschutz.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Koordinaten-Struktur, Planetentypen/Temperatur/Größe,
  ⭐ Monde (Phalanx/Sprungtor), Kolonisierung & Distanzklassen, ⭐ Frontier-Expansion &
  Regionen-Ringe, Decay/Karten-Hygiene, Deep Space/Expeditionen, Tuning-Hebel.
