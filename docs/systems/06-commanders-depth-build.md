# Bau-Spec: Kommandeur-Tiefe ("Charaktere mit Eigenleben")

> Stand 2026-06-10. Konkrete Umsetzung von [05-commanders.md](./05-commanders.md). Ziel (Nutzer):
> Kommandeure ins **Zentrum** rücken — echter Mehrwert + man investiert **gern Zeit** in sie. **Natürlicher
> Overkill** statt hartem Limit: wer zu viele anheuert, kann sie nicht alle zufriedenstellen → unzufriedene
> werden zum Problem. Jeder Angriff = bewusste Wahl, *wen* (und ob den wertvollen Legenden) man mitnimmt.
>
> Baut auf dem Bestehenden auf (Moral-Drift, Boni, Span, XP→Rang, Permadeath laufen schon).

## 0. Die Kern-Mechanik: Zufriedenheits-/Beziehungs-Ökonomie (der weiche Deckel)
**Loyalität (0–100) wird die Beziehungswährung** (heute toter Stat). Daneben ein **Unmut**-Akkumulator (`unrest`,
neues Feld 0–100).

- **Unmut wächst pro Tick**, und zwar **schneller, je stärker der Kommandeur** ist:
  `unrest += base_gain × rank_mult × grade_mult × trait_mult`.
  → **Macht korreliert mit Bedürftigkeit**: eine SSS-Legende ist eine Primadonna, ein C-Kadett genügsam.
  Beispiel (base 6/Tag): Legende-SSS-`ambitious` ≈ 6×2.5×2.0×1.5 ≈ **Forderung alle ~2 Tage**;
  Kadett-C ≈ 6×0.5×1.0 ≈ **alle ~3 Wochen**.
- **Senkt Unmut:** Siege/erfolgreiche Missionen (Einsatz befriedigt), erfüllte Forderungen, Landgang.
  **Hebt zusätzlich:** Untätigkeit (Neglect, existiert für Moral), Niederlage, Überdehnung.
- **Unmut ≥ Schwelle → erzeugt eine trait-gefärbte Forderung** (Transmission `requires_decision`, nutzt das
  vorhandene annehmen/ablehnen/verhandeln-System): `ambitious`→Beförderung/eigenes Geschwader, `greedy`→
  Beuteanteil, müde→Landgang, `aggressive`→„führ mich in den Kampf", Rivalität→„versetz X".
- **Erfüllen:** Loyalität ↑, Unmut-Reset, Kosten (Ressourcen / Span-Bindung / Moral-Tradeoff).
  **Ignorieren/Timeout:** Loyalität ↓, Unmut bleibt → Eskalation (Wiederholung, dann Meuterei/Überlauf).
- **Der Deckel entsteht von selbst:** Forderungen kommen über N starke Kommandeure schneller, als ein Spieler
  sie bedienen kann → Loyalität erodiert breit → man pflegt lieber **wenige, gut betreute** statt 500.
  Zweite Achse bleibt das vorhandene **Span-of-Control** (gleichzeitige Flotten-Einsätze).

## 1. Loyalitäts-Folgen (Zähne)
- **Meuterei** (im Kampf, `resolve_attack`/Flotte): bei Loyalität < `mutiny_threshold` (z. B. 30) Chance
  `(threshold−loyalty)/threshold × trait` → Flotte **verweigert** (kehrt unverrichtet um) oder kämpft mit
  Malus. `hot_tempered` erhöht, `loyal` ~eliminiert.
- **Überlauf** (untätig + Loyalität < `defect_threshold` z. B. 15): tägliche Chance → Kommandeur **verlässt**
  dich (Status `defected`); optional werden ihm zugewiesene Schiffe zu einem feindlichen NPC (emergent — später).
- Permadeath/Verwundung (existiert) bleibt die Kampf-Achse: den Legenden NICHT leichtfertig riskieren.

## 2. Traits, die zählen (tote Effekte verdrahten)
`combat_attack_mod` + `morale_decay_mult` laufen schon. Neu zu verdrahten (balance `personality_traits`):
- **cautious** `loss_reduction`/`retreat_early`: senkt eigene Verluste; bricht bei drohender Vernichtung früh ab.
- **ambitious** `xp_mult` (1.25) + `demands_promotion`; **greedy** `morale_on_loot` + fordert Beuteanteil.
- **honorable** `morale_on_fair_target`/`morale_on_bashing` (Ziel-Klassifikation: schwächeres Ziel = bashing).
- **charismatic** `adjacent_morale_boost`: hebt Moral der anderen aktiven Kommandeure des Spielers.
- **hot_tempered** `morale_instability` (stärkere Drift-Schwankung) + `mutiny_risk` (s. §1); **aggressive**
  `self_risk_mod` (höheres Permadeath-Risiko, höherer Schaden).

## 3. Aktive Fähigkeiten (Cooldown-Skills, Rang+Spezialisierung-gated)
Neuer balance-Block `commander.abilities`. Eine Fähigkeit je Kommandeur **vor dem Einsatz wählbar/scharf**, im
Kampf/Flug einmal wirksam, dann Cooldown. Beispiele (Doku 05 §6):
- Kampf: *Konzentriertes Feuer* (Erstrunden-Schaden ↑), *Moral-Rede* (temp. +Moral der Flotte).
- Logistik: *Eilmarsch* (Tempo ↑), *Notreparatur* (Verluste teils zurück).
- Spionage: *Tiefen-Scan* (Gegner-Intel beim Angriff), *Störsender* (Eskorte/Phalanx des Ziels schwächen).
- Macht die Frage **„welchen Kommandeur für welchen Angriff"** taktisch (Fit von Spezialisierung+Fähigkeit+Traits).

## 4. Gouverneurs-Rolle (zweite Verwendung, nutzt `economy_bonus`)
Kommandeur einem **Planeten** zuweisen (statt/neben Flotte): `economy_bonus.peak_pct_by_rank` (cadet 3 % …
legend 10 %) auf Produktion (+ optional Forschungs-/Bau-Tempo je Spezialisierung). Moral-skaliert. Auch ein
Gouverneur hat Unmut/Forderungen → auch „Daheim-Pflege" zählt. Gibt Nicht-Kämpfern Kommandeurs-Wert.
- **NEU (Nutzer 2026-06-10):** dafür braucht das Kadetten-Training eine **eigene Kategorie „Verwaltung/
  Gouverneur"** — neue Spezialisierung (specialization_enum-Wert, z. B. `admin`), planetenfokussiert (stärkere
  economy/Forschungs-Boni, schwache Kampfboni). Sonst gäbe es keine darauf spezialisierten Kommandeure.

## 5. Zahlen (Defaults, tunebar in balance.commander)
| Param | Default | Sinn |
|---|---|---|
| `satisfaction.base_gain_per_day` | 6 | Unmut-Grundzuwachs |
| `satisfaction.rank_mult` | cadet .5 / officer .8 / veteran 1.2 / elite 1.8 / legend 2.5 | starke = bedürftiger |
| `satisfaction.grade_mult` | = potency (C 1.0 … SSS 2.0) | Güteklasse skaliert Bedürftigkeit |
| `satisfaction.demand_threshold` | 100 | Unmut-Schwelle → Forderung |
| `satisfaction.relief_on_win` | 25 | Unmut-Senkung bei Sieg/Erfolg |
| `loyalty.start_academy` | 90 | Eigengewächse treu |
| `loyalty.fulfil_gain` / `ignore_loss` | +12 / −15 | Forderungs-Folgen |
| `loyalty.mutiny_threshold` / `defect_threshold` | 30 / 15 | Zähne |
| `abilities.base_cooldown_seconds` | 3600 | je Fähigkeit tunebar |

## 6. Build-Scheiben (jede verifizierbar + committet)
1. **Zufriedenheits-Ökonomie + Forderungs-Generator** (Felder `unrest`/`loyalty`-Nutzung, Tick, trait-getriebene
   Demand-Transmissions, Erfüllen/Ignorieren-Folgen, Unmut-Senkung bei Sieg). *Der Kern/weiche Deckel.*
2. **Loyalitäts-Folgen**: Meuterei (Kampf) + Überlauf (untätig).
3. **Traits, die zählen**: tote Effekte verdrahten (§2).
4. **Aktive Fähigkeiten**: balance-Block + Auswahl/Schärfen + Wirkung im Kampf/Flug.
5. **Gouverneurs-Rolle**: Planet-Zuweisung + economy_bonus.
6. **Frontend**: Loyalität/Unmut + nächste Forderung im Detail, Fähigkeit wählen, Gouverneur zuweisen; Forderungen
   im Postfach (decide existiert). + Tests, Deploy je Scheibe.

> Reihenfolge bewusst: Scheibe 1 ist das Herz (der Overkill-Deckel). Danach Zähne (2), Charakter (3), Taktik (4),
> Breite (5). Offene Mikro-Entscheidungen mit Defaults oben — beim Bauen bestätigen.
