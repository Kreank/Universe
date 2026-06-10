# Bau-Spec: Kommandeur-Entwicklung (Volle RPG-Zucht)

> Stand 2026-06-10. **Bewusster Schwenk:** Doc 05 §9 hatte „schlank, keine Skillpunkte" beschlossen
> (Anti-Meta). Nutzer-Entscheidung 2026-06-10: **volle RPG-Zucht** — Fähigkeiten erlernen/steigern/verlernen,
> Charakter (Traits) gezielt formen, den perfekten Kommandeur **hochzüchten** — und das alles **sichtbar**.
> Akzeptiert: Meta-Build-Risiko (über Kosten/Slots/Zufriedenheits-Ökonomie gebremst).
>
> Baut auf [06-commanders-depth-build.md](./06-commanders-depth-build.md) (Zufriedenheit/Loyalität/Traits laufen).

## 0. Leitidee
Ein Kommandeur wird ein **Projekt**: du investierst Skillpunkte + Ressourcen + Zeit, lernst/steigerst
Fähigkeiten, formst Traits — und **siehst** Effekte, Cooldowns, Risiken im UI. Der natürliche Overkill
(Zufriedenheit/Loyalität) bleibt die Bremse: je mehr/stärker, desto mehr Pflege.

## 1. Entwicklungs-Währung
- **Skillpunkte (`skill_points`, neues Feld):** beim **Rang-Aufstieg** vergeben (z. B. +1/Rang, +Grade-Bonus),
  optional zusätzlich kaufbar (Ressourcen→Punkte an der Akademie, gedeckelt). XP→Rang bleibt automatisch.
- Lernen/Steigern kostet Skillpunkte (+ ggf. Ressourcen + Zeit an einem Planeten mit Kommando-Akademie).

## 2. Fähigkeiten: erlernen / steigern / verlernen
- **Katalog** `balance.commander.ability_catalog`: viele Fähigkeiten, je `{key,label,category,max_level,
  effect_per_level,cost_per_level,requires:{min_rank,spec?,research?},cooldown_seconds}`. Manche spez-
  gebunden (combat/logistics/spy/research/admin), manche allgemein.
- **Commander.abilities** (JSONB): `[{key, level}]` — erlernte Fähigkeiten mit Stufe.
- **Erlernen:** Skillpunkte (+Res/Zeit) → Fähigkeit auf Stufe 1. **Steigern:** Stufe ↑ (stärkerer Effekt,
  evtl. kürzerer Cooldown). **Verlernen:** entfernen, Teil-Erstattung der Punkte.
- **Slots:** begrenzte **Arm-Slots** pro Einsatz (z. B. 1 bei cadet … bis 3 bei legend, +Grade). Erlernt ≠
  scharf: beim Versand wählst du, **welche** erlernte Fähigkeit du scharf schaltest → taktische Wahl
  „welcher Kommandeur + welche Fähigkeit für welchen Angriff".
- **Wirkung:** combat-Fähigkeiten in `resolve_attack`, logistics/utility in `send_fleet`/Missionen
  (Effekt skaliert mit Fähigkeitsstufe × Moral). Cooldown je Fähigkeit (`last_ability_at` → pro-Fähigkeit-Map).

## 3. Charakter formen (Trait-Zucht)
- **Charakter-Training** an der Akademie (Kosten Res + Zeit + evtl. Skillpunkte):
  - **Reroll** aller Traits, oder
  - gezielt **einen Trait ersetzen** (gegen einen gewünschten, teurer), oder
  - einen Trait **festschreiben/entfernen**.
- **Kadetten-Einfluss beim Training:** optional gegen Aufpreis **einen Wunsch-Trait garantieren** (Rest zufällig).
- So lässt sich der „perfekte" Kommandeur gezielt züchten — gebremst durch Kosten + dass starke Kommandeure
  bedürftiger sind (Zufriedenheits-Ökonomie).

## 4. Sichtbarkeit (war zu dünn — wird Teil jeder Scheibe)
- **Fähigkeits-Panel** (Detail): erlernte + erlernbare Fähigkeiten, Effekt, Stufe, Cooldown, bereit-Status,
  Lernen/Steigern/Verlernen-Buttons, Skillpunkte-Anzeige.
- **Trait-Tooltips** mit echten Effekten (statt nur Label).
- **Roster:** Loyalitäts-/Unmut-Risiko-Indikator; wer fordert/droht überzulaufen.
- **Versand:** Fähigkeits-Auswahl (welche scharf), mit Effekt/Cooldown.
- **Gouverneur:** angezeigter Produktions-Bonus.

## 5. Zahlen (Defaults, tunebar)
| Param | Default |
|---|---|
| skill_points je Rang-Aufstieg | 1 (+1 bei Grade ≥ A) |
| arm_slots nach Rang | cadet 1 / officer 1 / veteran 2 / elite 2 / legend 3 |
| ability cost_per_level | 1 Skillpunkt + Res (kategorie-/stufenabhängig) |
| unlearn-Erstattung | 50 % der Skillpunkte |
| Charakter-Reroll Kosten | Res + Zeit (akademie-skaliert); Wunsch-Trait teurer |
| ability max_level | 3 |

## 6. Build-Scheiben
1. **Fähigkeits-System** (Modell `abilities`/`skill_points` + Migration, Katalog, Skillpunkte bei Rang-Up,
   learn/upgrade/unlearn-Endpoints, Wirkung in Kampf/Flug, Arm-Slots + Auswahl) + **Fähigkeits-Panel-UI** + Versand-Auswahl.
2. **Trait-Zucht** (Charakter-Training-Endpoint: Reroll/Ersetzen/Festschreiben; Kadetten-Wunsch-Trait) + UI.
3. **Sichtbarkeits-Politur** (Trait-Tooltips mit Effekten, Loyalitäts-/Unmut-Risiko im Roster, Gouverneur-Bonus).
4. Tests + Deploy je Scheibe.

> Pivot dokumentiert: ersetzt Doc 05 §9-Entscheidung „schlank/keine Skillpunkte". Bremse gegen Meta-Builds =
> Slots + Kosten + Zufriedenheits-Ökonomie (bedürftige Top-Kommandeure), nicht Verzicht auf Tiefe.
