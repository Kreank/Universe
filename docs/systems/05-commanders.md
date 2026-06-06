# System-Design: Commander-Tiefe

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · vertieft **GDD §6** · koppelt an [04 Kampf](./04-combat-model.md), [01 Wirtschaft](./01-economy-and-buildings.md), [02 Techbaum](./02-technology-tree.md)
>
> Das Herzstück und Alleinstellungsmerkmal von *Universe*. Dieses Dokument konsolidiert und
> vertieft alles rund um Commander: Ränge, Traits, Moral, Span, Forderungen, aktive
> Fähigkeiten, Persona/LLM und Loyalität.

---

## 1. Designziele

1. **Bindung statt Zahlen** (GDD-Säule 1). Ein Commander soll sich wie eine *Person*
   anfühlen, in die man investiert — nicht wie ein Statbonus.
2. **Organische Veteranen-Bremse** (GDD-Säulen 2/3). Führung skaliert *nicht* linear:
   Span, Moral-Verfall und Permadeath-Risiko deckeln rohe Größe von selbst.
3. **Treibstoff für die KI-Schicht.** Persönlichkeiten liefern die Vorlagen für die
   Funkspruch-Banken (GDD §10) — je distinkter der Commander, desto besser die KI-Momente.

---

## 2. Ränge & Progression

Fünf Ränge (= Qualitätsstufen aus GDD §6.7). Aufstieg durch **Erfahrung (XP)** aus
Einsätzen passend zur Spezialisierung (Kämpfe, Missionen, Handel, Erkundung).

| Rang | Quelle (typisch) | Stat-Cap | Span-Beitrag | Permadeath-Schutz |
|------|------------------|:---:|:---:|:---:|
| **Kadett** | Akademie (grün) | niedrig | klein | gering |
| **Offizier** | Dienst/Anwerben | — | — | — |
| **Veteran** | viel Dienst | — | — | — |
| **Elite** | Top-Anwerbung, Bergung | hoch | groß | hoch |
| **Legende** | sehr lange gedient / einzigartige Funde | sehr hoch | sehr groß | sehr hoch |

- **XP & Level:** Commander sammeln XP → Stufenaufstieg innerhalb des Rangs → verbessert
  Werte und stärkt/schaltet Fähigkeiten frei. Rang-Aufstieg an XP-Schwellen + ggf. Bedingung
  (z. B. „X Siege").
- **Progressiver Wert:** Höhere Ränge sind teurer ersetzbar, schwerer permanent zu verlieren
  und ihr Tod hat größere Crew-Folgen (GDD §6.7).

> 🔧 **Fork:** Wie tief die Progression? Volles RPG (Level, Skillpunkte, freie Verteilung)
> vs. schlank (Rang + Traits + feste Fähigkeiten je Rang). → §9.

---

## 3. Traits (zwei Arten)

Jeder Commander hat **Persönlichkeits-Traits** (Verhalten/Story) und eine
**Spezialisierung** (mechanischer Fokus). Traits prägen Boni *und* Forderungen *und* den
LLM-Sprechstil.

### 3.1 Persönlichkeits-Traits (Beispiele)
| Trait | Wirkung (Beispiel) |
|-------|--------------------|
| **aggressiv** | +Angriff, aber höheres Eigenrisiko, drängt auf Kämpfe |
| **vorsichtig** | geringere Verluste/früher Rückzug, aber weniger Beute |
| **loyal** | langsamer Moral-Verfall, geringes Überlauf-Risiko |
| **ehrgeizig** | schneller XP, aber fordert Beförderungen/Kommando |
| **gierig** | +Kampfmoral bei Beute, fordert größeren Beuteanteil |
| **ehrenhaft** | Moral-Bonus bei fairen Zielen, **Malus bei Bashing** (GDD §8) |
| **charismatisch** | hebt Moral benachbarter Unter-Commander |
| **jähzornig** | starke Boni, aber instabile Moral / Meuterei-Risiko |

> ⭐ **Fork:** Sollen Traits auch echte **Nachteile** haben (Risiko/Belohnung, tiefere
> Persönlichkeiten) oder nur positive Boni (simpler, planbarer)? → §9.

### 3.2 Spezialisierungen (koppeln an Spielstile, GDD §5)
**Kampf · Logistik · Spionage · Forschung · Handel.** Bestimmt, welche aktiven Fähigkeiten
(§6) und passiven Boni ein Commander mitbringt und woraus er XP zieht.

---

## 4. Moral — das zentrale Modell

Moral (0–100) ist der Kern-Regelkreis. Sie **driftet** zu einem Basiswert, der sich aus der
jüngsten Behandlung ergibt; **Ereignisse** verschieben sie sofort.

**Hebt:** Siege, Beute, erfüllte Forderungen, Erholung im Heimathafen, Beförderung,
ehrenhafte Ziele (für ehrenhafte Traits).
**Senkt:** Niederlagen, Dauerkrieg ohne Pause, **Überdehnung** (Flotte > Span),
ignorierte Forderungen, **sinnloses Bashing** (GDD §8), **Vernachlässigung/Untätigkeit**
(Horten-Bremse — kein Sold, GDD §6.3).

**Bänder → Kampfwirkung (GDD §6.2):**

| Moral | Effekt |
|-------|--------|
| 80–100 | +10 % Angriff/Verteidigung der geführten Einheiten |
| 50–79 | neutral |
| 25–49 | −10 %, gelegentliche Befehlsverzögerung |
| 0–24 | −25 %, Risiko von Befehlsverweigerung / Meuterei / Überlaufen |

**Konzeptformel (zu tunen):**
```
ziel_moral   = basis + Σ(jüngste Behandlung)             // Trait-modifiziert
moral(t+1)   = moral(t) + erholungs_oder_verfallsrate × (ziel_moral − moral(t))
             + sofort_deltas (Sieg/Niederlage/Forderung/…)
```
- *loyal/charismatisch* → langsamerer Verfall / höhere Basis.
- *Logistiktechnik & Crew-Psychologie* (Doku 02) → schnellere Erholung / höhere Obergrenze.
- 🔧 Raten, Basiswerte, Deltas → Prototyp.

---

## 5. Span-of-Control (Führungs-Soft-Cap)

Der zentrale Mechanismus gegen lineares Veteranen-Wachstum (GDD §6.4):

- Jeder Commander hat eine **Führungskapazität** (Anzahl effektiv führbarer
  Unter-Commander / Geschwader).
- Des Spielers Gesamt-Span: **Basis 3**, + **Kommandozentrale** (Gebäude, Doku 01),
  + **Kommandodoktrin** (Tech, Doku 02) — jeweils mit **abnehmendem Ertrag**.
- **Überdehnung:** Flotte/Reich über der effektiven Span → Koordinationsstrafen
  (Befehlsverzögerung im Kampf, §04; Moral-Druck nach unten).
- Folge: Ein Veteran mit 10× Flotte kann sie **nicht** 10× effektiv einsetzen → abnehmende
  Erträge statt Übermacht.

---

## 6. Aktive Fähigkeiten (Entscheidung: vorhanden, GDD/Doku 04)

Zusätzlich zu passiven Moral-/Trait-Boni haben Commander **einsetzbare Fähigkeiten**
(Cooldown und/oder Moral-/Ressourcenkosten). Freischaltung nach **Rang + Spezialisierung**.

| Spezialisierung | Beispiel-Fähigkeiten |
|-----------------|----------------------|
| **Kampf** | *Konzentriertes Feuer* (Schaden bündeln), *Flankenmanöver*, *Moral-Rede* (temp. +Moral) |
| **Logistik** | *Eilmarsch* (Tempo↑), *Sparflug* (Sprit↓), *Notreparatur* |
| **Spionage** | *Tiefen-Scan*, *Störsender* (Gegen-Aufklärung), *Sabotage* |
| **Forschung** | *Heureka* (Forschungs-Boost), *Anomalie-Analyse* (bessere Expeditionsfunde) |
| **Handel** | *Marktcoup* (besserer Kurs), *Konvoi* (Frachtschutz) |

- **Rückzug** als universelle Aktion (vorsichtige Commander nutzen ihn auto-ausgelöst).
- 🔧 Umsetzungsreihenfolge: für Vertical Slice ggf. nur Modifikatoren, Fähigkeiten zügig
  nachziehen (Doku 04 §8).

---

## 7. Forderungs- & Entscheidungssystem

Macht passives Lesen zu aktivem Führungs-Gameplay (GDD §6.5):

- Commander stellen **Forderungen**, getrieben von Traits + Situation
  (z. B. *ehrgeizig* → „Gib mir ein eigenes Geschwader"; *gierig* → „größerer Beuteanteil";
  *erschöpft* → „Landurlaub").
- Der Spieler entscheidet per **Klick** (Mechanik braucht **kein** LLM; der LLM liefert nur
  den *Text* der Forderung/Reaktion via Bank, GDD §10).
- **Erfüllen** → Moral/Loyalität ↑ (evtl. Ressourcenkosten / Span-Bindung).
  **Ablehnen** → Moral ↓, bei instabilen Traits Eskalation bis Meuterei/Überlaufen.

---

## 8. Persona, LLM-Kopplung & Loyalität

- **Persona-Profil** (Name, Hintergrund, Sprechstil, Kern-Traits) wird bei Erstellung
  angelegt — Texte offline per LLM vorgenerierbar. Dient als fixer System-Prompt für die
  **Reaktions-Banken** (GDD §10.1/§10.5); **pgvector** dedupliziert (kein Wiederholen).
- **Loyalität** (eigener Wert, v. a. für **abgeworbene/gefangene** Commander, GDD §6.6):
  niedrige Loyalität + niedrige Moral → **Überlauf-/Meuterei-Risiko**. Loyale Eigengewächse
  (Akademie/Beförderung) starten hoch; Umgedrehte bleiben ein kalkuliertes Risiko.
- **Beschaffung & Permadeath:** siehe GDD §6.6/§6.7 und Kampf-Auflösung Doku 04 §5
  (hier nicht dupliziert).

---

## 9. Tuning-Hebel & offene Entscheidungen 🔧

1. **Progressionstiefe:** ✅ **Entscheidung (2026-06-06): schlank** — Aufstieg über Ränge,
   feste Fähigkeiten/Boni je Rang + Traits. Kein freies Skillpunkte-System (vermeidet
   Meta-Builds & Aufwand); Bindung entsteht über Persönlichkeit/Geschichte.
2. **Negative Traits:** ✅ **Entscheidung (2026-06-06): ja, Risiko/Belohnung** — Traits
   haben Vor- *und* Nachteile. Tiefere Persönlichkeiten, bessere LLM-Momente, passt zur
   Säule „Bindung statt Zahlen".
3. **Fähigkeits-Gating** — rein über Rang, rein über Spezialisierung, oder beides (Default: beides).
4. **Konkrete Zahlen** — Span-Werte, Moral-Raten/Deltas, XP-Schwellen, Loyalitäts-/
   Überlauf-Wahrscheinlichkeiten, Cooldowns → Prototyp (auch GDD §12.2).

---

## 10. Abhängigkeiten zu anderen System-Dokus

- **01 Wirtschaft** — Akademie (Beschaffung), Kommandozentrale (Span), Produktions-Bonus.
- **02 Techbaum** — Kommandodoktrin/Logistik/Crew-Psychologie/Kommunikation.
- **04 Kampf** — Moral-/Trait-Modifikatoren, aktive Fähigkeiten, Flaggschiff/Permadeath.
- **07 Flottenmissionen** — Commander führen Missionen, XP-Quellen.
- **GDD §6/§10** — Grundlagen, Beschaffung, Permadeath, KI-Funksprüche.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Ränge/XP, Traits (Persönlichkeit + Spezialisierung),
  Moral-Modell & Konzeptformel, Span-of-Control, aktive Fähigkeiten, Forderungssystem,
  Persona/LLM/Loyalität, Tuning-Hebel (Progressionstiefe, negative Traits).
