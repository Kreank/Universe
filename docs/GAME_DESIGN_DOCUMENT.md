# Game Design Document — Arbeitstitel: *Universe*

> **Status:** v0.2 (lebendes Dokument) · **Stand:** 2026-06-06 · **Autor:** Sascha (+ KI)
>
> Dieses Dokument ist die *Single Source of Truth* für das Spiel. Es wird laufend
> erweitert. Jede größere Entscheidung wird hier oder in einem ADR (Architecture
> Decision Record) festgehalten. Beim Entwickeln mit KI ist dieses Dokument der
> Kontext, der zu Beginn jeder Session gelesen wird — es muss daher eindeutig und
> widerspruchsfrei bleiben.
>
> **Navigation:** [Doku-Index (README)](./README.md) · [Architektur](./ARCHITECTURE.md) ·
> Detail-Designs unter [`docs/systems/`](./systems/) (01–12). Dieses GDD ist die Übersicht;
> die System-Dokus enthalten die Tiefe.

---

## System-Dokumente (Detail-Design)

Die folgenden Systeme sind im Detail ausgearbeitet (mit Tuning-Hebeln & getroffenen
Entscheidungen je Dokument). Übersicht & Entscheidungs-Schnellliste: [README](./README.md).

[01 Wirtschaft & Gebäude](./systems/01-economy-and-buildings.md) ·
[02 Technologiebaum](./systems/02-technology-tree.md) ·
[03 Schiffe & Einheiten](./systems/03-ships-and-units.md) ·
[04 Kampfmodell](./systems/04-combat-model.md) ·
[05 Commander-Tiefe](./systems/05-commanders.md) ·
[06 Universum & Karte](./systems/06-universe-and-map.md) ·
[07 Flottenmissionen](./systems/07-fleet-missions.md) ·
[08 NPC-Imperien & PvE](./systems/08-npc-empires.md) ·
[09 Allianzen & Diplomatie](./systems/09-alliances-and-diplomacy.md) ·
[10 Progression & Pacing](./systems/10-progression-and-pacing.md) ·
[11 Spielererlebnis (UX)](./systems/11-player-experience.md) ·
[12 Fairness & Monetarisierung](./systems/12-fairness-and-monetization.md)

---

## 1. Vision & Pitch

*Universe* ist ein browserbasiertes Weltraum-Aufbau-MMO in der Tradition von OGame:
Du startest mit einem Planeten, baust dein Reich aus, erforschst Technologien,
kommandierst Flotten und schließt dich Allianzen an. Drei Schwerpunkte stehen offen —
**Forschung/Erkundung**, **Militär/Piraterie** und **Wirtschaft/Handel** — die sich
frei kombinieren lassen.

Zwei Dinge unterscheiden *Universe* vom Genre-Klassiker:

1. **Persistentes Universum statt ständiger Resets.** Spieler müssen nicht alle paar
   Monate von vorn anfangen. Stattdessen sorgen Frontier-Expansion, Inaktivitäts-Decay
   und Saisons dafür, dass die Welt frisch und ausbalanciert bleibt.
2. **Lebendige KI-Crews.** Du befehligst nicht nur Schiffe, sondern **Flotten-Commander
   und deren Unter-Commander**, die eine Persönlichkeit haben, bei Laune gehalten werden
   müssen und über ein **Moral-System** organisch verhindern, dass Veteranen Neulinge
   einfach überrollen.

**Tagline (Arbeitsfassung):** *„Befehlige nicht nur Flotten — führe Menschen."*

---

## 2. Design-Säulen

Jede Feature-Entscheidung wird an diesen vier Säulen gemessen. Was keiner Säule dient,
fliegt raus.

1. **Bindung statt Zahlen.** Der emotionale Kern ist die Beziehung zu Commandern und
   Crew, nicht das reine Hochzählen von Flottenpunkten.
2. **Organische Balance.** Faire Bedingungen entstehen *diegetisch* (aus der Spielwelt
   heraus, z. B. sinkende Moral), nicht durch aufgesetzte Regeln und Verbots-Popups.
3. **Persistenz mit Frische.** Fortschritt bleibt erhalten; trotzdem fühlt sich die Welt
   nie „fertig" oder verstopft an.
4. **KI, die man spürt, aber nicht bezahlt.** KI macht das Spiel überall lebendig —
   teure LLM-Rechenzeit wird aber rationiert und auf seltene, bedeutungsvolle Momente
   konzentriert.

---

## 3. Kern-Loop (Core Gameplay Loop)

Der minütlich/stündlich laufende Grundzyklus, identisch zum Genre, aber mit Crew-Ebene:

```
Rohstoffe abbauen  →  Gebäude/Forschung/Flotten bauen  →  handeln / erkunden / angreifen
        ↑                                                              │
        └──────────  Beute, Moral, Commander-Entwicklung  ←───────────┘
```

1. **Produzieren:** Minen erzeugen Metall, Kristall, Deuterium (Echtzeit, auch offline).
2. **Investieren:** Rohstoffe in Gebäude, Forschung, Schiffe, Verteidigung stecken.
3. **Agieren:** je nach Spielstil erkunden, handeln oder raiden.
4. **Konsequenz:** Erfolge/Misserfolge wirken auf Commander-Moral und Reichs-Entwicklung
   zurück — der eigentliche Langzeit-Loop.

**Zeitskala:** Aufbau in Echtzeit (Tick-basiert, siehe Architektur-Doku). Flottenbewegung
mit realer Reisedauer. Ziel: für Casual-Spieler in 15–30 Min/Tag sinnvoll spielbar.

---

## 4. Ressourcen & Wirtschaft

| Ressource | Quelle | Verwendung |
|-----------|--------|------------|
| **Metall** | Metallmine | Basis für Gebäude & Schiffe |
| **Kristall** | Kristallmine | Elektronik, höherwertige Schiffe, Forschung |
| **Deuterium** | Deuterium-Synthetisierer | Treibstoff (Flottenflüge), Forschung, Fusionskraft |
| **Energie** | Solar-/Fusionskraftwerk | Betreibt Minen (kein Lagerbestand, muss gedeckt sein) |

Zusätzliche „weiche" Ressource:

- **Moral** (pro Commander / Crew) — siehe §6. Keine handelbare Ressource, sondern ein
  Zustand, der Boni/Mali auf Kampfwerte gibt.

**Wirtschafts-Grundsätze:**

- Lagerkapazität begrenzt Hortung (klassisch). Überlauf = Verlust → Anreiz zum Ausgeben.
- Inaktivitäts-Decay (§7) verhindert ewige Ressourcen-Anhäufung toter Accounts.
- Handel zwischen Spielern + NPC-Markt (KI-NPC-Imperien als Liquiditätsquelle, §9/§10).

---

## 5. Spielstile (drei Pfade, frei kombinierbar)

Es gibt **keine festen Klassen**. Ein Spieler kann mischen, spezialisiert sich aber durch
Forschungs- und Commander-Wahl. Jeder Pfad hat eigene Commander-Spezialisierungen (§6).

### 5.1 Forschung & Erkundung
- Schaltet Technologien, Antriebe, Spezialschiffe frei.
- Erkundet Anomalien, Wracks, unbekannte Sektoren (prozedural generiert, §10.3).
- Belohnung: Tech-Vorsprung, einzigartige Funde, Lore.

### 5.2 Militär & Piraterie
- Spionage, Angriffe, Plünderung, Trümmerfelder einsammeln.
- Stärkster, aber riskantester Pfad — und der, der am stärksten durch das Moral-/
  Anti-Bashing-System (§6, §8) reguliert wird.

### 5.3 Wirtschaft & Handel
- Effiziente Produktion, Handelsrouten, Markt-Arbitrage, Versorgung von Allianzen.
- Friedlicher Aufstieg über Reichtum; finanziert Söldner-Commander und Schutzbündnisse.

**Interaktion der Pfade:** Forscher liefern Tech, Händler liefern Ressourcen, Militärs
liefern Schutz/Beute. Das ist die ökonomische Grundlage für Allianzen (§9).

---

## 6. Commander- & Moral-System  ⭐ (Kern-Alleinstellungsmerkmal)

Das Herzstück. Du befehligst nicht abstrakte Schiffe, sondern eine **Befehlskette**:

```
Spieler (Admiral)
   └── Flotten-Commander        (führen Flottenverbände)
          └── Unter-Commander    (führen Geschwader / Sektionen)
                 └── Crew         (abstrahiert über Moral-Wert)
```

### 6.1 Commander-Eigenschaften
Jeder Commander hat:
- **Persönlichkeits-Traits** (z. B. *vorsichtig, aggressiv, loyal, ehrgeizig, gierig,
  ehrenhaft*) → beeinflussen Boni, Forderungen und Reaktionen.
- **Spezialisierung** passend zu den Pfaden (Kampf, Logistik, Spionage, Forschung, Handel).
- **Moral** (0–100). Wirkt als Multiplikator auf die Leistung der unterstellten Einheiten.
- **Persona-Profil** (kompakter Steckbrief: Name, Hintergrund, Sprechstil) → dient als
  fixer System-Prompt für KI-Funksprüche (§10.1).

### 6.2 Moral — was sie tut
Moral ist der zentrale Balance-Hebel. **Vorläufige** Werte (zu tunen):

| Moral | Effekt (Beispiel) |
|-------|-------------------|
| 80–100 | +10 % Angriff/Verteidigung der Einheiten dieses Commanders |
| 50–79 | neutral |
| 25–49 | −10 % Kampfwerte, gelegentliche Befehlsverzögerung |
| 0–24 | −25 % Kampfwerte, Risiko von Befehlsverweigerung / Meuterei / Überlaufen |

### 6.3 Was Moral hebt / senkt
**Kein Soldsystem** — Moral entsteht ausschließlich durch *Taten*, nicht durch Bezahlung.

- **Hebt:** Siege, Beute, Erholungsphasen, erfüllte Forderungen, Beförderung, ehrenhafte
  Ziele (für ehrenhafte Traits).
- **Senkt:** Niederlagen, Dauerkrieg ohne Pause, Überdehnung (zu viele Fronten),
  ignorierte Forderungen, sinnloses Bashing Schwächerer (§8), und **Vernachlässigung/
  Untätigkeit** — ungenutzte Commander verlieren langsam Moral (Horten-Bremse, §6.7).

### 6.4 Span of Control (der eigentliche Soft-Cap gegen Veteranen)
Ein Admiral/Commander kann nur eine **begrenzte Zahl** direkt unterstellter Commander
*effektiv* führen. Darüber hinaus entstehen **Koordinationsstrafen** (Befehlsverzögerung,
Moral-Druck nach unten).

- Effekt: Ein Veteran mit 10× Flotte kann sie **nicht** 10× so effektiv einsetzen.
  Rohe Größe stößt an Führungs-Grenzen → **abnehmende Erträge** statt linearer Skalierung.
- Erweiterbar durch Forschung/Gebäude (Kommandozentrale, Führungs-Tech), aber nie gratis.

### 6.5 Crew-Management als aktives Spiel
Commander stellen **Forderungen** (z. B. „Gib mir die 7. Flotte" oder „Wir brauchen
Landurlaub"). Der Spieler entscheidet per Klick (kein LLM nötig für die Entscheidung).
Die Wahl wirkt auf Moral und Trait-Entwicklung. So wird passives Lesen zu aktivem
Führungs-Gameplay.

### 6.6 Commander beschaffen (Akquise)
Jeder Spielstil hat seinen eigenen Beschaffungsweg, plus ein universeller Grundpfad:

- **Akademie (Grundpfad, alle):** *Kommando-Akademie* bauen, Kadetten ausbilden
  (Zeit + Ressourcen). Liefert grüne, schwache Commander — der **verlässliche Nachschub**,
  damit Permadeath nie eine Sackgasse ist. Steigen durch Dienst auf.
- **Anwerben (Wirtschaft/Handel):** erfahrene Commander gegen Ressourcen vom Markt/aus der
  Kantine rekrutieren; gelegentlich seltene mit Top-Traits. Reichtum = Auswahl.
- **Gefangennahme/Abwerben (Militär/Piraterie):** im Kampf gegnerische Commander gefangen
  nehmen → Lösegeld kassieren *oder* umdrehen (Loyalitätsrisiko: Umgedrehte können später
  überlaufen). Knüpft an die Capture-Mechanik (§6.7).
- **Bergung/Erkundung (Forschung/Erkunden):** Überlebende aus Wracks, Veteranen aus
  Anomalien, berühmte Entdecker anwerben. Einzigartige Funde.
- **Beförderung aus der Crew (emergent):** langgedienter Unter-Commander kann zum vollen
  Commander aufsteigen — belohnt, Crews am Leben zu halten.

### 6.7 Qualitätsstufen, Anzahl & Permadeath

**Qualitätsstufen:** grün (Akademie/billig) → Veteran → Elite/Legende
(gefangen/gefunden/lange gedient). Höhere Stufen = bessere Traits, größere Span, stärkere
Persona — und **progressiv schwerer endgültig zu verlieren**.

**Anzahl (emergenter Soft-Cap, keine harte Grenze):** Start mit **1**, Midgame **~3–5
aktiv** lohnenswert. Begrenzt wird die *nutzbare* Zahl durch:
- **Span of Control** (§6.4) — Koordinationsstrafe bei zu vielen Unterstellten,
- **Beschaffungskosten/-zeit**,
- **Moral-Verfall bei Vernachlässigung** (Horten-Bremse) — eine große Bank ungenutzter
  Commander *verrottet* moralisch und wird wertlos. Dies **ersetzt den (abgelehnten) Sold**
  als organische Bremse gegen Horten.

**Permadeath (gewählt: echter Permadeath) — mit drei Leitplanken, damit er Anti-Bashing
und Casual-Bindung nicht untergräbt:**
1. **Folge entscheidender Niederlage, nicht jeder Niederlage.** Es gibt eine Flucht-/
   Evakuierungschance; nur wer Flotte *und* Commander wirklich verliert, verliert ihn
   endgültig. Risiko bleibt kalkulierbar statt willkürlich.
2. **Neulingsschutz greift hart:** Unter Schutz (§8) kann **kein** Commander permakilled
   oder permanent gefangen werden.
3. **Progressiver Wert:** Höherrangige Commander sind schwerer endgültig zu verlieren;
   ihr Tod hat größere Trauer-/Crew-Konsequenzen → ein echtes, LLM-würdiges Ereignis
   („Wir haben Admiral X verloren").

---

## 7. Das persistente Universum

Kein periodischer Voll-Reset. Stattdessen drei Mechaniken, die Frische & Balance ohne
Verlust des Fortschritts sichern:

### 7.1 Frontier-Expansion
Neue Galaxien/Sektoren öffnen sich über die Zeit. **Neue Spieler starten an einer
frischen Grenze**, nicht zwischen Jahres-Veteranen. Alte Kernregionen werden zu
„entwickeltem Raum" mit eigener Dynamik (mehr Infrastruktur, mehr Konkurrenz, mehr Schutz).

### 7.2 Inaktivitäts-Decay
Ungepflegte Imperien zerfallen langsam: Moral sinkt, Kolonien fallen ab, Bestände
schrumpfen. Räumt die Karte ohne harten Reset und hält die Wirtschaft gesund.

### 7.3 Saisons (über dem persistenten Reich)
**Entscheidung:** Bei einem Saison-Wechsel werden **nur Ranglisten, Saison-Score und
Saison-Belohnungen** zurückgesetzt — das **Imperium bleibt vollständig erhalten**
(maximale Persistenz). **Default-Länge: quartalsweise** (tunebar). Das liefert das
„Neuanfang"-Gefühl und neue Wettkampf-Ziele, ohne dass Aufbau-Fortschritt verloren geht.

---

## 8. Balance & Anti-Bashing (diegetisch)

Ziel: Langjährige Spieler dürfen Neulinge **nicht** einfach farmen. Lösung nicht über
ein hässliches Verbots-Popup, sondern aus der Spielwelt heraus:

1. **Crew-Moral als Gewissen:** Greift ein starker Spieler wiederholt deutlich Schwächere
   an, sinkt die Moral *seiner eigenen* Crew („wir sind Soldaten/Piraten, keine Schlächter").
   Commander fordern lohnendere/ehrenhaftere Ziele. → Bashing bestraft sich selbst.
2. **Span of Control (§6.4):** begrenzt die effektive Schlagkraft der Größten.
3. **Score-/Tech-Banding beim Matchmaking:** Beute/Effekt skaliert ungünstig, wenn das
   Ziel weit unterlegen ist; Spionage-/Angriffs-Reichweite ggf. an Score-Differenz koppeln.
4. **Frontier-Trennung (§7.1):** Neulinge sind räumlich/strukturell von Veteranen getrennt.
5. **Neulingsschutz (Zeit + Score):** Schutz für X Tage **ODER** bis zu einem Score-Wert —
   was zuerst endet (robust gegen Ausnutzen). Während des Schutzes: keine Angriffe von
   weit Stärkeren und **kein Permadeath/keine permanente Gefangennahme** der eigenen
   Commander (§6.7). Konkrete Schwellen → Tuning im Prototyp.

Die Säule lautet **organische Balance** (§2.2) — Regel 1 verschmilzt die Anti-Bashing-
Mechanik mit dem Commander-System und macht sie zum Teil der Story.

---

## 9. Allianzen

- Spieler gründen/treten Allianzen bei (klassisch): gemeinsame Verteidigung, Handel,
  koordinierte Angriffe, geteilte Forschung/Logistik.
- Pfad-Synergie (§5): Forscher + Händler + Militär ergänzen sich innerhalb einer Allianz.
- **KI-Anknüpfung:** NPC-Imperien (§10.2) können Allianzen Angebote/Drohungen schicken;
  Diplomatie-Funksprüche werden bei seltenen Schlüsselmomenten per LLM erzeugt.
- *Detaillierte Allianz-Mechanik: später, nicht Teil des Vertical Slice (§13).*

---

## 10. KI-Architektur (vier Ebenen)

Leitprinzip (Säule §2.4): **Teure KI (LLM) nur für seltene, sichtbare, emotionale
Momente. Billige KI (Regeln, Behavior Trees, Telemetrie) für alles Permanente & Massenhafte.**

### 10.1 LLM-Commander (Dialog/Events)
Commander „sprechen" via lokalem LLM (Ollama). **Keine Live-Blocking-Calls.** Stattdessen
**vorgenerierte Reaktions-Banken** (siehe Content-Pipeline §10.5):

- Persona-Profil als fixer System-Prompt → Funksprüche klingen nach *diesem* Commander.
- pgvector zur **Deduplizierung** (kein Commander wiederholt sich) und für RAG-Kontext
  (Lore/Persona-Schnipsel als Generierungs-Input).

### 10.2 KI-Gegner / NPC-Imperien
Füllen das persistente Universum. **Kein LLM** für ihr Verhalten — Utility-AI /
Behavior Trees, skaliert auf Tausende. Sie expandieren, handeln, raiden, liefern
Markt-Liquidität und Herausforderung. LLM nur, wenn ein NPC **mit dem Spieler**
diplomatisch interagiert (selten).

### 10.3 Prozedurale Generierung
Universum, Anomalien, Quest-Hooks **algorithmisch & seeded** (deterministisch — wichtig
für ein MMO). LLM nur für *Texte obendrauf* (Lore, Beschreibungen) — **offline
vorgeneriert und gecacht**, praktisch kostenneutral im Betrieb.

### 10.4 Adaptive Balance
Telemetrie-System (kein ML-Modell nötig): beobachtet Angriffsmuster, erkennt
Veteran-vs-Neuling, und greift **diegetisch** über §8 ein (Crew-Moral, Forderungen).
Verschmilzt mit dem Commander-System statt externer Regel.

### 10.5 Content-Pipeline (der zentrale Trick: „Munition vs. Verschuss")

**Problem:** Spieler sind beim Angriff *online* — Reaktionen müssen *sofort* kommen.
**Lösung:** Trigger-Zeit von Generierungs-Zeit trennen.

- **Nachts (GPU idle):** Batch-Job füllt pro Commander **personalisierte Reaktions-Banken**
  (z. B. 10 Sieg-Varianten, 10 Niederlage-Varianten, Meuterei, knapper Sieg …), im Stil
  des jeweiligen Commanders. Außerdem: Banken nachfüllen, langsame Inhalte (gelangweilte
  Crew nach Inaktivität), Flavor-Pool, Lore.
- **Tagsüber live (0 ms, kein LLM):** Bei einem Event zieht das Spiel **sofort** eine
  passende Zeile aus der Bank + **Slot-Filling** der konkreten Details
  („Wir haben *[Feind]* bei *[Planet]* zerschlagen — *[Trait-Kommentar]*").
- **Großmomente (optional, Sekunden später):** Zweistufig — sofortige Instant-Zeile
  („SIEG! Bericht folgt."), dann pusht ein **Hintergrund-Worker** *einen* echten
  kontextbezogenen Funkspruch (2–5 s auf der RTX 3070) als „vollständigen Bericht" nach.
  Latenz wird als *„Funkverkehr über Lichtjahre"* zum Feature.

**Content-Ebenen nach Kosten getrennt:**

| Ebene | Inhalt | Erzeugung | Kosten |
|-------|--------|-----------|--------|
| 1 | Routine-Meldungen („Mine fertig") | Templates + Variablen | gratis, kein LLM |
| 2 | Situations-Reaktionen (Sieg, Moral, Kolonie) | Nächtliche Reaktions-Banken pro Commander | LLM nachts, Verschuss tagsüber instant |
| 3 | Flavor (Crew-Gerüchte, Smalltalk, Lore) | Rotierender Pool, wöchentlich erneuert | LLM nachts, niedrige Priorität |

---

## 11. Tech-Stack (Überblick)

> Details & Service-Grenzen kommen in die separate **Architektur-Doku** (nächster Schritt).

- **Backend / Game-Server:** Python + **FastAPI** (async; REST + WebSockets für Echtzeit).
- **Tick/Scheduler:** advanciert Ressourcen, Bau, Flottenbewegung (eigener Worker/Loop).
- **AI-Worker:** **eigener Prozess/Container**, konsumiert Job-Queue, ruft **Ollama**,
  schreibt Reaktions-Banken/Funksprüche in die DB. *Muss vom Game-Server entkoppelt sein,
  damit LLM-Latenz nie den Spiel-Tick blockiert.* (fundamentale Architekturentscheidung)
- **Datenbank:** **PostgreSQL + pgvector** (Spielstand + Funkspruch-Banken + Embeddings
  für Dedup/RAG).
- **Queue / Pub-Sub / Cache:** **Redis** (Combat-Events → AI-Worker, WebSocket-Pub-Sub).
- **LLM:** **Ollama**, lokal auf RTX 3070 (8 GB VRAM). Modellklasse: 7–8B Q4
  (Llama 3.1 8B / Qwen2.5 7B / Mistral 7B) für Dialoge; 3–4B für Durchsatz.
- **Frontend:** **Angular** (SPA, WebSocket-Anbindung).
- **Infra:** **Docker** / Docker-Compose für den gesamten Stack.

**Hardware-Realität (Dev-/Alpha-Box):** Ryzen 9 3900X · 32 GB RAM · RTX 3070 8 GB.
→ Reicht für Dev + kleine Alpha (Dutzende gleichzeitige Spieler bei seltenen LLM-Events).
Produktions-Skalierung später via dickerer GPU oder API-Fallback (Cloud-LLM für
Live-Großmomente, lokal fürs nächtliche Vorgenerieren).

---

## 12. Design-Entscheidungen

### 12.1 Beschlossen (2026-06-06)
1. **Commander-Permadeath:** ✅ **Echter Permadeath**, mit drei Leitplanken
   (Flucht-/Evakuierungschance, harter Neulingsschutz, progressiver Wert). Details §6.7.
2. **Commander-Beschaffung:** ✅ **Alle Pfade** — Akademie (Grundpfad) + Anwerben +
   Gefangennahme + Bergung + Beförderung. Details §6.6.
3. **Commander-Anzahl:** ✅ **Emergenter Soft-Cap** (Start 1, Midgame ~3–5 aktiv) über
   Span-of-Control, Beschaffungskosten und Moral-Verfall. Keine harte Grenze. Details §6.7.
4. **Soldsystem:** ✅ **Kein Sold.** Moral nur durch Taten; Horten-Bremse über
   Moral-Verfall bei Vernachlässigung (§6.3, §6.7).
5. **Saison-Modell:** ✅ **Nur Ranglisten/Score/Belohnungen** werden zurückgesetzt,
   Imperium bleibt; Default quartalsweise (§7.3).
6. **Neulingsschutz:** ✅ **Zeit + Score-Schwelle** (was zuerst endet); kein Permadeath
   unter Schutz (§8).

### 12.2 Noch offen / im Prototyp zu tunen
1. **Konkrete Span-of-Control-Zahlen** (§6.4) — Default: Start 3 direkt unterstellte,
   ausbaubar per Forschung. Feintuning im Prototyp.
2. **Exakte Schwellen Neulingsschutz** (Tage / Score) — Tuning im Prototyp.
3. **Moral-Verfallsrate** bei Vernachlässigung — Tuning im Prototyp.
4. **Loyalitäts-/Überlauf-Wahrscheinlichkeit** umgedrehter (abgeworbener) Commander.
5. **Saison-Belohnungen konkret** (was gibt es, wie übertragbar?).

---

## 13. Scope: Vertical Slice (v1) vs. später

**Disziplin-Regel (Säule + Methodik):** *Nicht das ganze MMO bauen.* Zuerst der
kleinste **durchgängige** Loop durch den **kompletten** Stack
(Angular → FastAPI → DB → AI-Worker → Ollama → zurück).

### In Scope (Vertical Slice)
- 1 Planet, 3 Rohstoffe + Energie, Tick-basierte Produktion (offline-fähig).
- 2–3 Gebäude bauen (Minen, Kraftwerk), 1 einfache Forschung.
- **1 Flotten-Commander mit Moral** + 1 simple Aktion (z. B. Patrouille/kleiner Angriff
  auf ein NPC-Ziel).
- **Eine Commander-Reaktion** über die volle Pipeline: Event → Bank-Lookup → Slot-Filling
  → Anzeige im Frontend (plus nächtlicher Bank-Füll-Job als Cron).
- Auth + ein Spielerkonto, persistenter Spielstand in PostgreSQL.

### Out of Scope (v1)
Allianzen, vollständiger PvP, NPC-Imperien mit Verhalten, prozedurale Galaxien-Generierung
im großen Stil, Saisons, Markt/Handel, mobile UI-Politur. → spätere Meilensteine.

---

## 14. Glossar

- **Tick:** diskreter Zeitschritt, in dem der Server Produktion/Bau/Bewegung fortschreibt.
- **Reaktions-Bank:** pro Commander vorgenerierter Vorrat an Funksprüchen je Situation.
- **Slot-Filling:** Einsetzen konkreter Live-Werte in vorgenerierte Vorlagen (ohne LLM).
- **Span of Control:** Zahl der von einem Commander effektiv führbaren Unterstellten.
- **Diegetisch:** aus der Spielwelt heraus erklärt (statt durch aufgesetzte Systemregel).
- **ADR:** Architecture Decision Record — kurzes Dokument je größerer Technik-Entscheidung.
- **RAG:** Retrieval-Augmented Generation — relevanter Kontext aus der DB wird dem LLM mitgegeben.

---

### Änderungshistorie
- **v0.2 (2026-06-06):** Offene Fragen aus §12 beschlossen: echter Permadeath (+ Leitplanken),
  Commander-Beschaffung (alle Pfade), emergenter Anzahl-Soft-Cap, kein Sold (Moral-Verfall
  als Horten-Bremse), Saison-Modell (nur Ranglisten/Belohnungen), Neulingsschutz (Zeit+Score).
  Neue Abschnitte §6.6/§6.7; §6.3, §7.3, §8, §12 aktualisiert.
- **v0.1 (2026-06-06):** Erststruktur aus Brainstorming. Kern-Loop, Spielstile,
  Commander/Moral-System, persistentes Universum, KI-Architektur & Content-Pipeline,
  Tech-Stack, offene Fragen, Vertical-Slice-Scope.
