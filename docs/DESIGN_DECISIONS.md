# Design-Decisions — konkrete Zahlenwerte (Vertical Slice)

> **Stand:** 2026-06-06 · Ergänzt GDD §12.2 und die „Tuning-Hebel"-Abschnitte der System-Dokus.
> Hier werden die im Design **offen gelassenen Zahlenwerte** für den Vertical Slice festgelegt,
> damit die Implementierung starten kann. Alle Werte sind **tunebar** und leben in
> [`shared/balance.json`](../shared/balance.json) (Single Source of Truth — Backend und Frontend
> laden diese Datei, kein hartes Kopieren von Zahlen in Code).

## Methodik
Wo das Design einen Korridor oder „→ Prototyp" vorgab, wurde ein konkreter, begründeter
Startwert gewählt. Wo eine Entscheidung bereits getroffen war (GDD §12.1), wurde sie übernommen.

---

## 1. Welt & Pacing
| Punkt | Entscheidung | Begründung |
|-------|--------------|------------|
| **Universe-Speed** | **×7** | Mitte des beschlossenen Korridors 5–10 (GDD §12.1). Fortschritt in Stunden, casual-freundlich. |
| Universumsgröße (Slice) | 3 Galaxien × 100 Systeme × 15 Positionen | Klein genug für lokale Alpha, groß genug für Frontier-Gefühl. |
| Grundeinkommen | +30 Metall/h, +15 Kristall/h | OGame-Standard (Doku 01 §3). |
| Start-Lager | 10.000 je Ressource | Doku 01 §6-Formel bei niedriger Stufe. |

## 2. Commander & Moral
| Punkt | Entscheidung | Begründung |
|-------|--------------|------------|
| **Span-of-Control Basis** | **3** direkt unterstellte | GDD §12.2 Default. |
| Kommandozentrale-Bonus | +1, +1, +1, +1, +1, 0, +1, 0, +1, 0 (je Stufe) | Abnehmender Ertrag (Doku 01 §7.2), keine unbegrenzte Kette. |
| Überdehnungs-Strafe | −8 % effektive Kampfkraft je Geschwader über Span | Spürbar, aber nicht vernichtend (Doku 05 §5). |
| **Moral-Start / Basis** | Start 60, Basis-Ziel 50 | Neutrales Band (50–79), Raum nach oben/unten. |
| Moral-Drift-Rate | 0,10 × (Ziel − Ist) pro Stunden-Tick | Sanfte Annäherung; loyal/charismatisch halbieren Verfall. |
| **Neglect-Decay** | nach 3 Tagen Untätigkeit −2 Moral/Tag | Horten-Bremse (kein Sold, GDD §6.3). |
| Moral-Deltas | Sieg +8, Niederlage −12, Forderung erfüllt +6 / ignoriert −6, Beförderung +12, Bashing −10 | Niederlagen wiegen schwerer als Siege (Risikogefühl). |
| Negative Traits | **ja** (Risiko/Belohnung) | GDD §12.1 / Doku 05 §9. |
| Progression | **schlank** (Rang + Traits, kein freies Skill-System) | Doku 05 §9.1. |
| Wirtschafts-Bonus | bis +10 % Produktion × (Moral/100), rangabhängig | Doku 01 §3. |

## 3. Kampf
| Punkt | Entscheidung | Begründung |
|-------|--------------|------------|
| **Rundenzahl** | **6** | Doku 04 §8 Default. |
| Schild-Abprall | Schaden < 1 % Schild prallt ab | Klassen-Relevanz (Doku 04 §2). |
| Explosionsschwelle | unter 70 % Hülle: Chance = 1 − Resthülle/Maxhülle | Doku 04 §2/§5. |
| **Trümmer-Anteil** | **30 %** der zerstörten Schiffe (M+K), Verteidigung erzeugt keine | Doku 04 §8. |
| **Plünderquote** | **50 %** ungeschützter Ressourcen, durch Fracht begrenzt | Doku 04 §3. |
| Verteidigungs-Regen | **70 %** nach Kampf | Verteidigung langfristig lohnend (Doku 04 §3). |
| **Evakuierung** | nur wenn eigene Schiffe überleben; Basis 30 % + Rang + Logistik + Überlebende | GDD §12.1, Doku 04 §8.2. |

## 4. Schiffe (konkreter Slice-Roster)
Leichter Jäger, Schwerer Jäger, Kreuzer, Kleiner Transporter, Spionagesonde — OGame-nahe Werte
in `balance.json`. Hülle = (Metall+Kristall)/10. Rapidfire: Kreuzer→Leichter Jäger ×6 etc.

## 5. Forschung
| Punkt | Entscheidung |
|-------|--------------|
| **Parallel** | genau **eine** Forschung gleichzeitig (Doku 02 §7.1). |
| Zeitformel | (M+K) / (1000 × (1+Labor) × Speed) Stunden. |
| Kosten | Basis × 2^(lvl−1). |

## 6. Flotte
| Punkt | Entscheidung |
|-------|--------------|
| Flottenslots | 1 + Computertechnik-Stufe (Doku 07 §2). |
| Fleetsave | klassisch (Flug + Rückruf), Bunker-Option später (GDD §12.1). |
| Sprit | Distanz × Schiffe × Tempo-Faktor; gedrosselter Flug spart Sprit. |

## 7. Schutz & Persistenz
| Punkt | Entscheidung |
|-------|--------------|
| **Neulingsschutz** | 7 Tage **ODER** Score 5.000 — was zuerst endet (GDD §12.1). Kein Permadeath/Plunder unter Schutz. |
| Inaktivitäts-Decay | ab 14 Tagen −5 %/Tag Produktion; Urlaubsmodus pausiert alles (Doku 01 §8). |
| Saison | nur Score/Ranglisten reset, Imperium bleibt (GDD §7.3) — außerhalb Slice-Scope. |

---

## Vertical-Slice-Loop (was end-to-end funktioniert)
1. Registrieren → Heimatplanet + Start-Commander.
2. Minen/Kraftwerk ausbauen → Ressourcen wachsen lazy, Energie drosselt.
3. Eine Forschung starten (z. B. Verbrennungstriebwerk).
4. Schiffe in der Werft bauen.
5. Flotte mit Commander auf NPC-Ziel (Angriff) schicken.
6. Kampf wird autoritativ berechnet → Combat-Report, Beute, Trümmer, Moral-Verschiebung.
7. **Commander-Funkspruch** über die volle Pipeline: Event → Bank-Lookup → Slot-Filling → WS-Push ins Postfach.
8. Nächtlicher AI-Worker-Job füllt die Reaktions-Banken pro Commander via Ollama nach.
