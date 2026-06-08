# Rollen-basiertes Kampf- & Schiffssystem (v2-Design)

> **Status:** v0.1-Design · **Stand:** 2026-06-07 · evolviert [03 Schiffe](./03-ships-and-units.md),
> [03a Roster](./03a-combat-ships-roadmap.md), [04 Kampf](./04-combat-model.md).
> **Kernidee:** Schiffe sind **keine lineare Machtleiter** (OGame-Problem), sondern **Rollen mit
> Konter-Beziehungen**. Tiefe entsteht aus **Flottenzusammenstellung + Waffenladung**, nicht aus Micro.

---

## 1. Was wir SCHON haben (Ausgangspunkt)

- Engine (`combat/engine.py`): 2 Subsysteme **Schild + Hülle**, Rapidfire-Ketten, Schild-Abprall,
  Explosion <70 % Hülle, Tech-/Commander-Boni. Rundenbasiert, deterministisch (Seed).
- Roster (03a): 14 Schiffe / 10 Verteidigung, eher OGame-linear; Rapidfire = bisherige „Tiefe".

**Diese v2 ist eine EVOLUTION, kein Neubau:** wir behalten Rundenmodell, Determinismus, Schild/Hülle
und ergänzen die fehlenden Achsen.

## 2. Die drei Subsysteme (NEU: Antrieb als eigenes System)

| System | Funktion | Bei Beschädigung | Ziel von |
|--------|----------|------------------|----------|
| **Schild** | regenerierender Puffer, regeneriert pro Runde (Hülle NICHT) | schützt Antrieb/Hülle solange >0 | jeder Angreifer zuerst |
| **Antrieb** | Tempo/Initiative/**Flucht** | „Mission Kill" ohne Zerstörung | **Pirat** (Hauptziel) |
| **Hülle** | HP **+ Frachtraum** | bei 0 zerstört → Fracht wird Wrackgut | Killer (Pirat will sie heil!) |

**Antrieb in Stufen** (graduell statt binär): 100–66 % volle Speed · 66–33 % reduziert ·
<33 % keine Flucht · 0 % **gestrandet**.

**Zielzustand `gestrandet` = Schild 0 UND Antrieb lahmgelegt** → erst dann kann ein Enterschiff kapern.

## 3. Waffen-Schadenstypen (das Herz der „disable statt destroy"-Tiefe)

Jede Waffe trifft Subsysteme unterschiedlich (Effektivitäts-Matrix in `balance.json`):

| Schadenstyp | Schild | Antrieb | Hülle | Absicht |
|-------------|:--:|:--:|:--:|---------|
| **Energie (Laser)** | ●●● | ● | ● | Schilde knacken |
| **Kinetik (Projektil)** | ✗ (prallt ab) | ●● | ●●● | töten/Hülle brechen |
| **Ionen / EMP** | ●●● | ●●● | ✗ | **Schilde leeren + Antrieb lahmlegen** (Piraten-Waffe) |
| **Raketen** | ● | ●● | ●●● | hoher Hüllenschaden, von **Punktverteidigung** abfangbar |

→ Gleiche Schiffe, anderer Ausgang je Ladung: *Killer* = Energie→Kinetik→Hülle. *Pirat* = Ionen→Antrieb→**entern**.

## 4. Flucht, Interdiktion, Entern (der Piraterie-Loop)

- **Disengage-Wurf** pro Runde: Chance = f(Antriebs-Integrität, relative Geschwindigkeit).
- **Interdiktor** setzt Disengage ≈ 0 (Fang-Feld) → ohne ihn ist schnelle Beute einfach weg → **zwingend für Piraterie**.
- **Entern**: nur gegen `gestrandet`; Enterschiff kapert **Fracht** oder das **ganze Schiff** (Loyalitäts-/Capture-Logik, koppelt an Doku 04 §5 Permadeath/Capture, die wir schon teilweise haben).
- **Eskorte kontert**: **Schild-Tender** pumpt Schilde nach (verhindert `gestrandet`-Fenster), **Punktverteidigung** killt Enterer/Raketen. Hält die Eskorte das Fenster zu → Pirat bricht ab (kein Loot, Sprit verbrannt).

## 5. Rollen-Roster (Mapping 03a → Rollen + NEUE Typen)

| Klasse | Rolle | aus 03a vorhanden? |
|--------|-------|--------------------|
| **Wirtschaft** | Frachter, **Bergbauschiff/Miner** ✚, Bergungsschiff (≈Recycler), Kolonieschiff, Späher (≈Sonde) | teils — Miner NEU |
| **Piraterie** | **Enterschiff** ✚, **Interdiktor/Fangschiff** ✚, **EWAR-Fregatte** ✚, **Tarnkappen-Korvette** ✚ | alle NEU |
| **Eskorte** | **Eskort-Fregatte** ✚, **Schild-Tender** ✚, **Abfangjäger** ✚ | alle NEU |
| **Linie** | Jäger (≈leichter Jäger), Kreuzer, Schlachtschiff (Tank), **Artillerieschiff** (≈Zerstörer, Standoff), **Träger** ✚, Großkampfschiff (≈Todesstern) | teils — Träger NEU |

**Konter-Dreieck (offener Kampf):** Schwarm schlägt Artillerie (unter die Geschütze) → Artillerie
schlägt Linientanks (Überreichweite) → Flak/Linie schlägt Schwarm (Flächenschaden). Jede Komposition hat einen Konter.

**Spielstile fallen heraus:** reiner **Händler** (Frachter + angeheuerte Eskorte) · **Pirat**
(Interdiktor+Enterer+Stealth) · **Söldner/Eskorten-Anbieter** (verkauft Schutz) — keiner braucht die volle Militär-Tech.

## 6. Build-Pfad (Phasen, jede für sich testbar)

1. ✅ **GEBAUT (2026-06-08) — Engine-Evolution:** Antrieb als 3. Subsystem (`drive`, persistenter
   Schaden → „mission kill", regeneriert NICHT) + **Schadenstyp×Subsystem-Matrix**
   (`combat.damage_matrix`: energy/kinetic/ion/missile × {shield,drive,hull}) + **Reichweiten-Bänder**
   (`combat.range_bands`: Distanz schließt sich far→near, Standoff-Strafe je Band). Schiffsprofile in
   `combat_roster` (weapon_type/drive/range), Engine liest sie datengetrieben. Rapidfire bleibt.
   Verifiziert: 11 Tests grün; Sim zeigt Standoff-Zerfall (Artillerie 20k→10k→5k) + Ionen-mission-kill.
   - **Kinetik-vs-Schild = 0.25** (nicht 0.0 wie im Design-Ideal „prallt ab"): mit dem aktuellen
     Dünn-Schild-Roster erzeugte 0.0 degenerierte Patt-Kämpfe. Tunebar Richtung 0, sobald
     Ionen-/Schild-Strip-Schiffe existieren. In `balance.json` dokumentiert.
   - **Konter-Dreieck noch gedämpft:** Schwarm killt Artillerie noch nicht (alte Destroyer-Stats =
     500 Schild). Volle Wirkung erst nach **Stat-Neutierung des Rosters (Phase 4)** — Phase 1 liefert
     den Mechanismus, nicht die finale Balance.
   - *Ursprünglicher Plan:* Schiffe bekommen `weapon_type` + Schild/Antrieb/Hülle-Stats. Rapidfire optional.
2. ✅ **GEBAUT (2026-06-08) — Strand/Disengage/Interdiktion:** Antriebs-Stufen (`combat.drive_stages`:
   voll/reduziert/bewegungsunfähig/gestrandet) + **Disengage-Wurf** pro Runde für die unterlegene
   Seite (`combat.disengage`, Power-Verhältnis-Trigger, Antrieb-`flee_factor`-gated) + **Interdiktions-Hook**
   (`combat_roster.interdictor=true` → Disengage→0). Engine-Default: **Angreifer darf fliehen** (Rückzug),
   Verteidiger hält Stellung — emergent sichtbar: hoffnungslos unterlegene Angreifer-Flotten ziehen sich
   zurück statt vernichtet zu werden (Geflohene überleben, gelten nicht als Verlust, Feld bleibt beim
   Verteidiger). Result: `attacker_fled`/`defender_fled` + `*_drive_disabled` (= enterbar, Phase 3).
   Verifiziert: 14 Tests grün. **Offen (Phase 3+):** echte Prey-Flucht im Fleet-vs-Fleet (Interception
   aus 03a Phase 3) + Tempo-Wirkung der Antriebs-Stufen auf die Flugzeit (braucht Pro-Schiff-drive-Persistenz).
3. ✅ **GEBAUT (2026-06-08) — Entern/Capture:** überlebende Enterschiffe (`combat_roster.boarder`)
   kapern gestrandete Gegner (Antrieb 0) nach der Rundenschleife — symmetrisch, unabhängig vom
   Sieger; `balance.combat.boarding.capture_per_boarder`. Result: `attacker_captured`/`defender_captured`.
   Service hängt gekaperte Schiffe an Flotte/Garnison (nur Schiffe, Commander nie). Verifiziert
   (34 Tests + Sim + E2E). Offen: Fracht-Bonus für gekaperte Frachter (überlappt mit Plunder).
4. ✅ **GEBAUT (2026-06-08) — Rollen-Roster + Eskort-Konter:** alle 12 neuen Spezial-Schiffe (§5 ✚)
   integriert (`balance.ships` + `combat_roster` + Frontend/Werft + Assets, universell baubar). Die
   **Eskort-Konter** stehen (`balance.combat.escort`): **Punktverteidigung** (Eskort-Fregatte) fängt
   Enterer ab (neutralisiert Enter-Kapazität); **Schild-Tender** repariert Antriebe pro Runde (kontert
   das Ionen-/Strand-Fenster). Damit ist die Piraterie-Schere-Stein-Papier komplett.
   **Sondermechaniken GEBAUT:** Tarnkappen-**Hinterhalt** (Überraschungsrunde, `combat.ambush`) +
   **Träger-Drohnen** (ephemere Staffeln, `combat.carrier`). Offen: **Mining/Expedition** als
   Wirtschafts-Loops, **Sensor-Entdeckung** als Stealth-Konter, **Stat-Neutierung der ALTEN
   Artillerie** (Konter-Dreieck offener Kampf spürbar machen).
5. **Spielstil-Layer:** Söldner-/Eskorten-Anheuern, Piraterie-Reputation (Wirtschafts-/Sozial-Schicht).

## 7. Entscheidungen

- **Rapidfire behalten** als *Schwarm-vs-klein*-Würze; **Schadenstyp×Subsystem** = primäre Tiefe. ✅
- **03a-Roster bleibt** (mappt auf Rollen), neue Rollen ergänzen — kein Wegwerfen. ✅
- **Reichweite/Standoff: ECHTE Reichweiten-Bänder** (Nutzer-Entscheidung 2026-06-07) — Schiffe in
  Distanz-Bändern, die sich pro Runde annähern; Artillerie feuert aus Überreichweite, Schwarm muss
  erst heran. Spieler sollen beim Flottenaufbau **strategisch denken**. → Engine bekommt eine
  **Distanz-/Initiative-Achse** (neu). ✅
- **Capture = nur SCHIFFE** (Nutzer-Entscheidung): Frachter → Frachter **+ Ressourcen**; andere → nur
  das Schiff. **Commander werden NIE gekapert** (bleiben beim Spieler; „Entlassen" ist separates,
  noch nicht integriertes Feature). → entkoppelt Entern von Permadeath, simpler & klarer. ✅
- **Eskorten/Söldner = sowohl NPC ALS AUCH Spieler-zu-Spieler** (Nutzer-Entscheidung): Kern ist die
  **Spieler-Interaktion** (Söldner-/Schutz-Geschäft zwischen Spielern). → eigener Sozial-/Markt-Layer
  (spätere Phase); die Eskort-Schiffsrollen werden aber unabhängig davon gebraucht. ✅

### Klassen-/Doktrin-System (Tech-Gating der Rollen) — Empfehlung, noch zu bestätigen
**Soft-Spezialisierung statt harter OGame-Klassenwahl.** Begründung: Bei einem **Konter-System**
(Schere-Stein-Papier) ist ein *harter* Klassen-Lock gefährlich — wer in den „falschen" Konter gesperrt
ist, sitzt fest, und die spannenden Pivot-Geschichten („ich werde Pirat") sterben.
- **Doktrin früh wählbar** (z. B. Militär/Kriegsherr · Handel · Piraterie · Forscher) → **passive Boni
  + billigerer/schnellerer Zugang** zur Signatur-Linie (ggf. ein einzigartiges Flaggschiff/Faehigkeit).
- **Alle Pfade technisch offen**, aber andere Linien sind **teurer/langsamer** → Spezialisierung lohnt,
  Konter-Dreieck bleibt intakt (niemand hat billig alles), Spieler-Handel/Söldner wird *gefördert*.
- **Doktrin-Wechsel gegen Kosten/Cooldown** (kein dauerhafter Trap → fair für persistentes MMO/Neulinge).
- **Synergie mit Bestehendem:** Commander-**Spezialisierungen** (combat/logistics/spy/research/trade)
  + `command_doctrine`-Tech existieren schon → Doktrin = Imperiums-Ebene, Commander = Crew-Ebene.

## 9. Die Doktrinen (Soft-Klassen) — konkret

Jede Doktrin: **passive Boni + günstigerer/schnellerer Zugang** zur Signatur-Linie + eine
**Doktrin-Fähigkeit/Flaggschiff**. Fremde Linien bleiben baubar, aber teurer/langsamer.
Werte = Prototyp (tunebar in `balance.json`).

### ⚠️ Grundprinzip: Universelle Basis vs. Signatur (WICHTIG)
**Doktrinen sperren KEINE Kernmechanik weg — sie geben nur Boni darauf.** Sonst entstehen Sackgassen
(z. B. „Kriegsherr kann nie kolonisieren").
- **Universell (ALLE Spieler, Kernspiel):** **Kolonieschiff** (Expansion ist Pflicht-Mechanik!),
  Basis-Frachter/Transporter, Basis-Jäger/Kreuzer, Basis-Verteidigung, Späher/Sonde.
- **Signatur (doktrin-vergünstigt, für andere teurer/später):** die *Spezial-Rollen* — Großkampfschiff/
  Träger/Artillerie (Militär), großer Miner & Handelsboni (Händler), Interdiktor/Enterer/EWAR/Stealth
  (Freibeuter), Expeditions-/Tief-Aufklärungs-Schiffe (Pionier).
- **Faustregel:** Was man zum *normalen Spielen/Wachsen* braucht → universell. Was einen *Spielstil*
  ausmacht → Signatur (Bonus, nicht Exklusiv-Lock). Piraterie-Schiffe dürfen am ehesten „exklusiv-ish"
  sein, weil Piraterie ein *optionaler* Aggressiv-Stil ist — Kolonisieren ist es nicht.

### ⚔️ Kriegsherr (Militär)
- **Fantasie:** offene Kriegsführung, Linienflotten, Eroberung.
- **Signatur:** Schlachtschiff (Tank), Artillerieschiff, Träger, Großkampfschiff.
- **Boni:** −15 % Kosten/Zeit Kampfschiffe · +10 % Waffenschaden · +1 Flottenslot · günstigere Waffen-/Panzerungs-Tech.
- **Fähigkeit:** „Konzentriertes Feuer" (Fokus-Salve im Kampf) oder einzigartiges Linien-Flaggschiff.
- **Schwäche:** teure Wirtschafts-/Stealth-Schiffe → braucht Beute/Handel für Nachschub.

### 💱 Händler (Handel)
- **Fantasie:** Logistik, Frachtimperium, Marktmacht.
- **Signatur:** Frachter, Großer Transporter, Bergbauschiff.
- **Boni:** +25 % Frachtkapazität · +20 % Markt-/Handels-Ertrag (geringere Marktgebühr) · −15 % Transporter-Kosten · **bessere Söldner-Anheuer-Konditionen**.
- **Fähigkeit:** Handelsrouten / passives Markt-Einkommen.
- **Schwäche:** schwache Kampf-Linie → **muss Eskorten anheuern** (Kern der Spieler-Interaktion).

### 🏴‍☠️ Freibeuter (Piraterie)
- **Fantasie:** disable & board, Hinterhalt, Beute.
- **Signatur:** Interdiktor, Enterschiff, EWAR-Fregatte, Tarnkappen-Korvette.
- **Boni:** −15 % Kosten Piraterie-Schiffe · +Enter-Erfolg · +Stealth (später entdeckt) · +Beute-Anteil · stärkeres Fang-Feld.
- **Fähigkeit:** „Hinterhalt" (Überraschungs-Runde: erste Runde nur der Pirat feuert/interdictet).
- **Schwäche:** schwache stehende Verteidigung/Wirtschaft; **Piraterie-Reputation → NPC-/Spieler-Vergeltung**.

### 🔭 Pionier (Forscher)
- **Fantasie:** Erkundung, Expeditionen, Tech-Vorsprung — der **beste Kolonisierer**, nicht der einzige.
- **Signatur (exklusiv/vergünstigt):** Tief-Aufklärer/Langstrecken-Späher, Expeditions-Schiffe.
  *(Kolonieschiff ist UNIVERSELL — alle können kolonisieren; der Pionier nur billiger/weiter/mehr.)*
- **Boni:** +Sensorreichweite · +Expeditions-Belohnung · −Forschungszeit · **−Kolonieschiff-Kosten + Kolonie-Limit** · weiter entfernte Kolonie-Ziele erreichbar.
- **Fähigkeit:** Tief-Aufklärung (mehr Spionage-Detail) / früher Tech-Zugriff.
- **Schwäche:** militärisch schwächer.

### Eskorte/Söldner — cross-cutting (kein eigener Tech-Lock)
**Entscheidung (2026-06-07): cross-cutting Service für ALLE — keine eigene Doktrin.**
Eskort-Schiffe (Eskort-Fregatte, Schild-Tender, Abfangjäger, Punktverteidigung) sind **für alle**
baubar; **Militär + Händler** bekommen leichte Eskort-Boni. Das **Söldner-/Schutz-Geschäft** ist ein
**Markt-/Sozial-Layer** (jeder bietet/heuert Schutz an) — der eigentliche Spieler-Interaktions-Loop.
Bleibt damit Tätigkeit/Markt, kein Tech-Pfad. → **System steht bei 4 Doktrinen.**

### Regeln
- **Doktrin früh wählbar** (nach Tutorial/Schutzphase), **Wechsel gegen Kosten + Cooldown**.
- Boni greifen über `balance.json` (Kosten-/Zeit-/Stat-Multiplikatoren je Doktrin) — wie Commander-Boni.
- Doktrin = **Imperiums-Ebene**; Commander-Spezialisierung = **Crew-Ebene** (ergänzen sich).

---

## 8. Asset-Bedarf (neu, über den aktuellen Satz hinaus)

- **Neue Schiff-Rollen** (§5 ✚): Miner, Enterschiff, Interdiktor, EWAR-Fregatte, Tarnkappen-Korvette,
  Eskort-Fregatte, Schild-Tender, Abfangjäger, Träger — je ein hochwertiges PNG im bestehenden Stil.
- **Waffen-/Schadenstyp-Icons:** Energie, Kinetik, Ionen/EMP, Rakete (für Ladung-Auswahl/UI).
- **Status-Icons:** Schild down, Antrieb beschädigt (Stufen), **gestrandet**, Interdiktions-Feld, Entern.
- **Effekte:** Ionen/EMP-Treffer, Enter-/Kaper-Effekt, Warp-Disruptor (ergänzend zu shield_hit/explosion).
