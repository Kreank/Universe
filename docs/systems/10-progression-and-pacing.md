# System-Design: Progression & Pacing

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · bindet alle Systeme zusammen · koppelt eng an GDD §7 (persistentes Universum) & §8 (Balance)
>
> Die Spielerreise über Wochen/Monate: Phasen, Ziele, Scoring, Saisons, Langzeit-Motivation
> und — kritisch für ein Universum **ohne Reset** — **Aufhol-Mechaniken** für Neueinsteiger.

---

## 1. Designziele

1. **Immer ein nächstes Ziel.** Auf jeder Stufe ein klares „Wozu" (kurz-, mittel-, langfristig).
2. **Neueinsteiger haben eine Chance** (GDD §8). In einer alten, persistenten Welt darf der
   Start nicht aussichtslos sein.
3. **Status statt Sieg.** Es gibt kein „Spiel gewonnen" — Motivation sind Ranglisten,
   Territorium, legendäre Commander und Saison-Titel.

---

## 2. Spielphasen

| Phase | Wo | Fokus & Ziele |
|-------|----|---------------|
| **Early — Frontier-Neuling** | Frontier (geschützt, Doku 06) | Loop lernen, erste Minen, erster Commander (Akademie), erste PvE-Kämpfe, erste Kolonie. *Ziel: stabile Wirtschaft.* |
| **Mid — Etablierung** | Mitte | Spezialisierung auf einen Pfad (GDD §5), Allianz beitreten, erstes echtes PvP/Expeditionen, Commander-Roster aufbauen. *Ziel: Nische finden, wachsen.* |
| **Late — Macht & Kern** | Kern | Großes Reich, Elite/Legenden-Commander, Allianzkriege, Territorium, Megaprojekte, Superschiff, Saison-Wettkampf. *Ziel: Dominanz & Legacy.* |

Der Aufstieg „nach innen" (Frontier → Kern, Doku 06) ist die räumliche Manifestation der Progression.

---

## 3. Scoring & Ranglisten

- **Punkte** aus Gebäuden, Forschung, Flotte, Wirtschaft (klassisch) — plus ⭐
  **Erkundungs-** und **Commander-Score** (Tiefe des Roster/Legenden).
- **Mehrere Ranglisten:** Gesamt, Militär, Wirtschaft, Forschung, Erkunder — damit jeder
  Spielstil (GDD §5) seine eigene „Bestenliste" hat und sich Spezialisierung lohnt.
- **Allianz-Ranglisten** analog (Doku 09).

---

## 4. Saisons & Belohnungen (GDD §7.3)

- **Quartalsweise** werden Saison-Score, Ranking und Saison-Ziele zurückgesetzt — das
  **Imperium bleibt** (Persistenz).
- **Saison-Ziele:** rotierende Herausforderungen (PvE, PvP, Wirtschaft, Erkundung) für Solo
  & Allianz.
- **⭐ Belohnungen sind Status, keine Macht** (Anti-P2W & Fairness, Doku 12): Titel,
  Abzeichen, kosmetische Schiffs-/Commander-Skins, Hall-of-Fame-Einträge, evtl. kleine,
  *nicht* kampfentscheidende Komfort-Boni.

---

## 5. Langzeit-Motivation (North Star)

Kein hartes Sieg-Ende. Stattdessen dauerhafte „Wozu"-Anker:

- **Ranglisten-Spitze** (Gesamt oder Spezialisierung).
- **Territorium** halten/ausdehnen (Doku 09).
- **⭐ Legendäre Commander** aufbauen — als persönliches Status-Symbol mit eigener Geschichte
  (LLM-Lore, GDD §10). Ein Permadeath einer Legende wird ein erinnerbares Ereignis
  (Memorial/Hall of Fame).
- **Saison-Titel** sammeln.

---

## 6. Retention-Loops

| Rhythmus | Was zieht zurück |
|----------|------------------|
| **Täglich** | Ressourcen/Bau prüfen, Missionen, **Commander-Forderungen & Funksprüche** (GDD §10), PvE-Raids |
| **Wöchentlich** | Expeditionen, Allianz-Operationen, Flavor-Rotation (GDD §10.5), Markt |
| **Saisonal** | Saison-Ziele, Ranglisten-Endstand, neue Titel/Belohnungen |

> ⭐ Die **nächtlich generierten Commander-Funksprüche** (GDD §10.5) sind ein bewusster
> täglicher Wiederkehr-Anker: „Was meldet meine Crew heute?"

---

## 7. ⭐ Aufhol-Mechaniken (kritisch für persistente Welt)

Damit Neueinsteiger in einem Monate alten Universum nicht chancenlos sind (GDD §8):

- **Frontier-Schutz & PvE-Onramp** (Doku 06/08) — geschützter, lebendiger Einstieg.
- **Flacherer Frühverlauf** — die ersten Stufen gehen schnell (Universe-Speed ×5–10,
  Doku 01); Veteranen-Vorsprung wirkt sich erst spät stark aus.
- **Newcomer-Boosts** — zeitlich begrenzte Start-Hilfen (z. B. erhöhte Produktion in den
  ersten Tagen), klar abgegrenzt von Pay-Vorteilen.
- **Mentor/Allianz-Förderung** — Allianzen können Neulinge gezielt unterstützen (Bank,
  Schutz, ACS-Verteidigung).
- **Plateau-Tendenz oben** — durch Span-of-Control & Moral-Verfall (Doku 05) wächst rohe
  Macht der Spitze nicht unbegrenzt → der Abstand schließt sich von beiden Seiten.

> 🔧 **Fork:** Wie *aggressiv* die Aufholhilfe? Stark (Neulinge rampen schnell, Spitze
> plateauisiert deutlich) vs. mild (sanfte Hilfe, Vorsprung bleibt spürbar). → §9.

---

## 8. Onboarding-Anbindung

Die Early-Phase wird vom Onboarding getragen (Details Doku 11 Spielererlebnis): geführte
erste Schritte, erster Commander als „Tutor"-Stimme (LLM-Funksprüche!), klare nächste Ziele.

---

## 9. Tuning-Hebel & offene Entscheidungen 🔧

1. **North-Star-Gewichtung:** ✅ **Entscheidung (2026-06-06): Hybrid** — strukturierte
   Saison-Ziele als Leitplanken UND Sandbox-Freiheit (Ranglisten, Territorium, Legenden).
   Spricht ziel- und freiheitsorientierte Spieler an.
2. **Aufhol-Stärke:** ✅ **Entscheidung (2026-06-06): stark** — Neulinge rampen schnell,
   Spitze plateauisiert deutlich (Span/Moral). Stärkster Anti-Bashing-Effekt & beste
   Casual-Bindung.
3. **Score-Gewichte, Saison-Länge (Default Quartal), konkrete Boost-Werte/-Dauern,
   Belohnungs-Katalog** → Prototyp.

---

## 10. Abhängigkeiten zu anderen System-Dokus

- **Alle Systeme** liefern Punkte/Ziele.
- **06 Universum** — Frontier→Kern als räumliche Progression, Decay.
- **08 NPC** — PvE-Onramp & -Inhalt.
- **09 Allianzen** — Allianz-Scoring, Territorium, Mentor-Förderung.
- **11 Spielererlebnis** — Onboarding, Daily Loop, Benachrichtigungen.
- **12 Fairness** — Status-statt-Macht-Belohnungen, Anti-P2W.
- **GDD §7/§8/§10** — Persistenz, Anti-Bashing, KI-Funksprüche als Retention.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Spielphasen (Frontier→Kern), Scoring/Ranglisten je
  Spielstil, Saisons & Status-Belohnungen, North Star (inkl. ⭐ Commander-Legacy),
  Retention-Loops, ⭐ Aufhol-Mechaniken, Tuning-Hebel (North-Star-Gewichtung, Aufhol-Stärke).
