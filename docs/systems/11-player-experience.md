# System-Design: Spielererlebnis (UX)

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · Frontend = Angular SPA (Architektur §3) · koppelt an [10 Progression](./10-progression-and-pacing.md)
>
> Wie sich das Spiel anfühlt und bedient: Navigation, Onboarding, der tägliche Loop und
> Benachrichtigungen. ⭐ = Universe-spezifisch.

---

## 1. Designziele

1. **Tiefe ohne Überforderung.** Komplexe Systeme, aber schrittweise eingeführt und klar
   dargestellt (transparente Formeln, Tooltips, Simulator).
2. **⭐ Die Crew steht im Zentrum.** Commander/Funksprüche sind kein Nebenmenü, sondern ein
   Haupt-Hub — das ist der emotionale Kern (GDD-Säule 1).
3. **Respekt vor der Zeit.** In 15–30 Min/Tag sinnvoll spielbar (GDD §3); kein Pflicht-
   „immer online".

---

## 2. Informationsarchitektur (Screens)

| Screen | Inhalt |
|--------|--------|
| **Übersicht / Dashboard** | Ressourcen, laufende Bau-/Forschungs-Queues, Alerts, anstehende Ankünfte |
| **Gebäude** | Planet ausbauen (Doku 01), pro Planet |
| **Forschung** | Techbaum (Doku 02), eine Forschung gleichzeitig |
| **Werft & Verteidigung** | Schiffe/Verteidigung bauen (Doku 03) |
| **Flotte** | Missionen senden, laufende Bewegungen, Rückruf, Fleetsave/Bunker (Doku 07) |
| **Galaxie / Karte** | [G:S:P]-Ansicht, Nachbarn, Ziele, Territorium-Grenzen (Doku 06/09) |
| **⭐ Kommandozentrale** | Commander-Roster, Moral, Zuweisungen, Ränge, aktive Fähigkeiten (Doku 05) |
| **⭐ Postfach / Funksprüche** | Transmissionen, Forderungen (mit Entscheidungs-Buttons), Kampfberichte (GDD §10) |
| **Allianz** | Mitglieder, Diplomatie, ACS, Bank, Megaprojekte (Doku 09) |
| **Markt / Handel** | Angebote, Routen, NPC-Händler (Doku 01/08) |
| **Ranglisten / Saison** | Scores je Spielstil, Saison-Ziele (Doku 10) |
| **Kampf-Simulator** | Schlacht vorab durchrechnen (Doku 04) |

---

## 3. ⭐ Commander- & Funkspruch-UX (Herzstück)

- **Kommandozentrale** als zentraler Hub: Roster mit Moral-Anzeige, Trait-/Rang-Übersicht,
  Zuweisung zu Flotten/Planeten, ein Klick zu „Geschichte" eines Commanders (gesammelte
  Funksprüche/Lore).
- **„Eingehende Transmission":** Funksprüche erscheinen in Echtzeit (WS-Push, Architektur
  §5.2) — sofortige Reaktion aus der Bank, Großmoment-Bericht wird Sekunden später
  „nachgereicht" (fühlt sich an wie Funk über Lichtjahre, GDD §10.5).
- **Forderungen** mit klaren **Entscheidungs-Buttons** (Erfüllen/Ablehnen/Verhandeln) —
  Mechanik ohne LLM, Text aus der Bank (Doku 05 §7).
- **Permadeath/Verlust** wird würdevoll inszeniert (Memorial-Eintrag, Crew-Reaktion) statt
  trockener Fehlermeldung.

---

## 4. Onboarding

- **Geschützter Frontier-Start** (Doku 06) + **flacher Frühverlauf** (Doku 10 §7).
- **Erster Commander als Tutor-Stimme:** führt per Funkspruch durch die ersten Schritte
  (LLM-Flavor, aber Schritte regelbasiert/gescriptet) — Tutorial *im* Spielton statt
  Pop-up-Wand.
- **Progressive Disclosure:** Systeme werden nacheinander freigeschaltet/erklärt (erst
  Wirtschaft, dann Flotte, dann Commander-Tiefe, dann Allianz), nicht alles auf einmal.
- **Klare nächste Ziele** (Quest-/Checklisten-artig), an die Early-Phase gekoppelt (Doku 10).

---

## 5. Daily Loop (15–30 Min)

```
Login → Funksprüche/Berichte lesen → Commander-Forderungen entscheiden →
Bau-/Forschungs-Queues füllen → Missionen/Raids/Expeditionen senden →
Karte/Markt checken → Fleetsave/Bunker falls offline-Risiko → Logout
```
Ziel: effizient, mit klaren Alerts; kein Zwang zu Mikromanagement-Marathons.

---

## 6. Benachrichtigungen (kritisch)

| Ereignis | Kanal |
|----------|-------|
| **⚠ Eingehender Angriff** (Fleetsave-Warnung!) | In-App + Push + (opt.) E-Mail |
| Bau/Forschung fertig, Flotte zurück, Expedition fertig | In-App + opt. Push |
| **⭐ Commander-Krise/Forderung** (Meuterei-Risiko, dringende Forderung) | In-App + opt. Push |
| Allianz/ACS-Aufruf | In-App + opt. Push |

- Die **Angriffswarnung** ist die wichtigste Benachrichtigung (entscheidet über Fleetsave,
  Doku 07). Technisch: WS-Push (Architektur §5.2) + externer Kanal, granular abschaltbar.

---

## 7. Plattform & Quality-of-Life

- **Web-first, responsiv** (Angular SPA): ein Codebase, läuft auf Desktop **und** Mobile-
  Browser. Genre wird viel mobil gespielt → Touch-taugliche Layouts von Anfang an.
- **QoL:** Bau-Queues, Flotten-Vorlagen, planetenübergreifende Ressourcen-Übersicht,
  Shortcuts, Sammel-Aktionen, transparente Tooltips mit Formelwerten.

> 🔧 **Fork:** Reicht **web-first responsiv** (auch mobil), oder ist eine dedizierte
> **native Mobile-App** ein erklärtes Ziel (mehr Aufwand, bessere Push/Performance)? → §9.

---

## 8. Barrierefreiheit & Klarheit

Lesbare Kontraste, skalierbare Schrift, klare Iconografie; alle Kernformeln (Produktion,
Bauzeit, Kampf) für Spieler einsehbar → planbares, faires Spiel.

---

## 9. Tuning-Hebel & offene Entscheidungen 🔧

1. **Plattform-Ziel:** ✅ **Entscheidung (2026-06-06): Web (Angular SPA) + native
   Mobile-App.** Beide Clients teilen sich dieselbe API (FastAPI, Architektur §3) — die
   saubere Server/Client-Trennung macht das möglich. Reihenfolge: Web zuerst, native App
   als erklärtes Folgeziel (eigene Codebase, bessere Push/Performance).
2. **Benachrichtigungs-Kanäle:** ✅ **Entscheidung (2026-06-06): In-App + Push** (granular
   abschaltbar). Push deckt die kritische Angriffswarnung auch offline ab; E-Mail vorerst
   nicht nötig.
3. **Konkrete Screen-Layouts, Onboarding-Schrittfolge, Alert-Schwellen** → Prototyp/Design-Phase.

---

## 10. Abhängigkeiten zu anderen System-Dokus

- **Architektur §3/§5.2** — WS-Push für Echtzeit-Updates & Funksprüche.
- **05 Commander / GDD §10** — Kommandozentrale, Funkspruch-UX, Forderungen.
- **07 Missionen** — Fleetsave/Bunker, Angriffswarnung.
- **10 Progression** — Onboarding, Daily-Loop, Saison-Anzeige.
- **04 Kampf** — Simulator, Kampfberichte.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Informationsarchitektur, ⭐ Commander-/Funkspruch-UX,
  Onboarding (Commander als Tutor), Daily Loop, Benachrichtigungen (Angriffswarnung),
  Plattform/QoL, Tuning-Hebel (Mobile-App, Benachrichtigungskanäle).
