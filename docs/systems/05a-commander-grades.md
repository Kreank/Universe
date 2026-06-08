# Commander-Güteklassen (F–SSS) — Design

> **Status:** v0.1-Plan · **Stand:** 2026-06-07 · ergänzt [05 Commander](./05-commanders.md) / GDD §6.
> Neuer **Seltenheits-/Potenzial-Grad** je Commander, orthogonal zum Rang.

---

## 1. Grad ≠ Rang

- **Rang** (Kadett · Offizier · Veteran · Elite · Legende): wächst durch **XP/Einsatz** —
  *erworbene Erfahrung*. Bleibt wie bisher.
- **Grad** (F · E · D · C · B · A · S · SS · SSS): **angeborenes Potenzial**, fix bei „Geburt".
  Skaliert, **wie stark** ein Commander ist — gleiche Boni-Arten, aber höhere Magnitude/Decke.

Ein SSS-Kadett startet schwach (niedriger Rang), hat aber das mit Abstand höchste Endpotenzial.

## 2. Grad-Wirkung (`potency`-Faktor)

Ein Multiplikator auf die Commander-Effektivität (greift in `commander/bonuses.py`):

| Grad | F | E | D | C | B | A | S | SS | SSS |
|------|--|--|--|--|--|--|--|--|--|
| `potency` | 0.60 | 0.75 | 0.90 | 1.00 | 1.15 | 1.30 | 1.50 | 1.75 | **2.00** |

Wirkt auf: **Schiffsklassen-Boni** (Angriff/Schild/Tempo), **Moral-Decke**, **Span-of-Control**,
optional **XP-Rate**. → Ein SSS-Commander ist ~2× so wirksam wie ein C bei gleichem Rang/Spezialisierung.
(`C` = Normalniveau/Baseline, damit alte Werte unverändert bleiben.)

## 3. Erwerb

### 3.1 Akademie-Ausbildung mit Investition (NEU: kostet Ressourcen)
Heute ist Kadetten-Ausbildung gratis → künftig **Investitions-Stufe wählbar**; mehr Ressourcen
verschieben die Grad-Verteilung nach oben. **SSS ist auch bei Maximal-Investition selten** (Prestige).

| Stufe | Kosten (×Basis) | F–D | C | B | A | S | SS | **SSS** |
|-------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Standard** | 1× | 85 | 12 | 3 | 0 | 0 | 0 | 0 |
| **Gehoben** | 3× | 45 | 30 | 18 | 6 | 1 | 0 | 0 |
| **Elite** | 8× | 25 | 20 | 30 | 21.5 | 3 | 0.5 | 0 |
| **Experimentell** | 20× | 5 | 15 | 30 | 30 | 12 | 3 | **5** |

> **Max SSS = 5 %** (nur „Experimentell"). Entscheidung getroffen — bewusst niedrig, damit ein
> SSS ein echtes Ereignis bleibt, nicht kaufbar. Alle Zahlen leben in `balance.json`, tunebar.

### 3.2 Expeditionen
Können Commander **jeden Grades** finden — seltene High-Grades als Belohnung fürs Erkunden
(eigene, flachere Verteilung mit kleiner S+-Chance). Koppelt an die spätere `expedition`-Mission.

## 4. Umsetzungs-Skizze
1. `commanders.grade`-Spalte (Enum F..SSS) + Migration; Default `C` für Bestands-Commander.
2. `balance.json` → `commander.grades`: `potency`-Tabelle + Ausbildungs-Stufen + Wahrscheinlichkeiten.
3. Ausbildungs-Flow: Investitions-Stufe wählen → Ressourcen abziehen → Grad gewichtet würfeln
   (seeded) → Commander mit Grad anlegen. `bonus-preview` um Grad erweitern.
4. `bonuses.py`: alle Boni × `potency(grade)`; Span/Moral-Decke ebenso.
5. Frontend: Grad-Badge (F–SSS, farbcodiert) auf Commander-Karten + Investitions-Stufen-Auswahl
   in der Akademie.

> **Balancing-Wächter:** Grad-Potency koppelt an Late-Game-Macht → zusammen mit Span/Permadeath
> testen, damit ein einzelner SSS-Veteran kein Selbstläufer wird (vgl. Doku 03 §6, Todesstern).
