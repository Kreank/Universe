# Universe — Frontend-Redesign: Recherche-Grundlage & Design-Richtung

> Stand 2026-06-13. Grundlage für das Redesign auf **modern-cinematic Sci-Fi**, **voll
> gleichwertig responsiv**, verankert an **EVE Online / Stellaris** (Tiefe) + **OGame/Ikariam**
> (Erbe). Quelle: Tiefenrecherche (5 Such-Winkel, 24 Quellen, 110 Claims → 25 adversarial
> verifiziert/bestätigt 3-0) + Ist-Zustands-Audit des aktuellen Angular-Frontends.

## 0. Quellengüte — was ist BELEGT, was ist DESIGNENTSCHEIDUNG

**Belegt durch Primärquellen + 3-Stimmen-Verifikation** (hohe Konfidenz):
Navigation/Informationsarchitektur, EVE-Photon-Design-System-Prinzip, Glass/Depth-Technik,
Datendichte auf Mobile, CSS-Effekt-Performance, Accessibility (APCA/Touch-Targets).

**NICHT als Best-Practice belegt** (von der Recherche ausdrücklich als offen markiert) → hier
als **begründete Designentscheidung** gekennzeichnet, nicht als Quellen-Fakt:
Onboarding/FTUE-Muster, konkrete Typo-/Font-Pairings, Token-Wert-Skalen (Spacing/Elevation/
Radius/Motion), Zahlenformat-Konventionen, Vergleichs-Fallstudien Stellaris/STFC/Hades' Star.
→ Für diese Bereiche ist eine fokussierte Folge-Recherche möglich (siehe §10).

---

## 1. Ist-Zustand (Audit des aktuellen Frontends)

Die *Bausteine* sind da (dunkles Sci-Fi-Token-System in `styles.scss`, 13 Feature-Screens,
Shell mit Topbar/Sidenav/Kolonien-Leiste). Der „gewollt-nicht-gekonnt"-Eindruck kommt aus
**systemischen Lücken**, nicht aus fehlendem Konzept:

| Bereich | Ist-Schwäche |
|---|---|
| Token-System | Keine **Spacing-Skala** (Abstände ad-hoc in rem), nur **ein** Schatten (keine Elevation-Stufen), keine **Motion-Tokens** |
| Typografie | **System-Font** (`Segoe UI`) → wirkt sofort „Web-App", nicht „Spiel" |
| Hintergrund | **4 überlagerte Layer** (2 Radial-Gradients + Sternfeld-Tile + Abdunkler) + Glow auf vielen Elementen → **visuelles Rauschen** statt gezielter Tiefe |
| Konsistenz | Styles **pro Komponente verstreut** → Drift zwischen Screens (= Kernursache des Amateur-Eindrucks) |
| Navigation | **12 flache Nav-Items** ohne Gruppierung; **doppelter** Planetenwechsler (Topbar-Dropdown + Kolonien-Leiste); Mobile = nur Burger-Drawer (kein Bottom-Nav) |
| Icons | **Emoji-Glyphs** als Fallback gemischt mit PNG-Icons → Stilbruch |
| Gut gelöst | Persistente Ressourcen-Leiste mit Raten, Angriffs-Banner, Unread-Badge |

---

## 2. Navigation & Informationsarchitektur  ✅ BELEGT

**Erkenntnis (NN/g):** Persistente **links-vertikale Navigation** ist der robusteste Desktop-Anker
für eine breite, wachsende IA: skaliert auf beliebig viele Top-Level-Einträge ohne Redesign,
nutzt die ~80% Links-Aufmerksamkeit, scant pro Fixation effizienter, **übersetzt sich nahtlos auf
Mobile**. [nngroup.com/articles/vertical-nav]

**Erkenntnis (EVE/CCP):** EVE trennt Navigation in **zwei Ebenen** — eine anpassbare, persistente
**Schnellzugriffs-Leiste** (NeoCom, pin-/sortierbar) + ein **vollständiges, nicht-anpassbares
Feature-Verzeichnis** (EVE-Menü). So bleiben häufige Screens feste Anker, neue/seltene Features
bleiben auffindbar, ohne die Leiste zu überladen. [eveonline.com/news/neo-neocom-1]

**Erkenntnis (NN/g):** Mobile = **immer sichtbare Tab-Bar**, aber **max. 4–5 Einträge** (sonst
Touch-Targets zu klein). Versteckte Hamburger-Navigation senkt Nutzung („out of sight, out of
mind", sichtbare Nav wird ~1,5× so oft genutzt) → nur für selten genutzte Bereiche.
[nngroup.com/articles/mobile-navigation-patterns; /hamburger-menus]

**→ Konkret für Universe:**
- **Desktop:** linke, persistente Sidebar, **nach Domänen gruppiert** statt 12 flach:
  - *Imperium:* Dashboard · Gebäude · Forschung · Techbaum · Werft
  - *Militär:* Flotte · Simulator · Galaxie
  - *Reich & Sozial:* Handel · Kommandozentrale · Postfach · Rangliste
  - Auf Icon-Rail **kollabierbar** für Dichte; aktiver Zustand klar markiert („wo bin ich").
- **Mobile:** **Bottom-Tab-Bar mit 5** (Dashboard · Bau · Flotte · Galaxie · **Mehr**), Rest im
  „Mehr"-Drawer. Die Ressourcen-Leiste bleibt oben persistent.
- **Redundanz auflösen:** EINEN Planeten-/Kolonie-Wechsler (nicht Dropdown *und* Leiste).
  Empfehlung: kompakter Planet-Switcher in der Topbar + optional ausklappbare Kolonien-Liste.

---

## 3. Visuelles Design-System & Politur  ✅ BELEGT (Prinzip) / 🎨 Token-Werte = Designentscheidung

**Erkenntnis (EVE Photon):** Der „AAA-cinematic statt billig"-Look entsteht **primär durch ein
vereinheitlichtes Komponenten-System** — alle Buttons/Tabs/Header in *einem* kohärenten Stil; ein
Design-System ist „mehr als ein Style-Guide" (inkl. UI-Framework + Abbau technischer Schuld +
Beseitigung von Inkonsistenzen). **Inkonsistenz ist die Hauptursache** des Amateur-Eindrucks.
[eveonline.com/news/improving-photon-ui]

**Erkenntnis (EVE-Designziele):** „**Less operating system, more Sci-Fi**"; die UI soll die
Weltraum-Szene **ergänzen statt blockieren**. → Panels rahmen die Atmosphäre, kleistern sie nicht zu.
[eveonline.com/news/a-new-look-for-eves-ui-feedback-needed]

**Erkenntnis (EVE + MDN):** Glass/Depth = **blurred, desaturierte, helligkeits-gefilterte
See-Through-Panels** mit **3 abgestuften Transparenzzuständen** (aktiv = am klarsten, inaktiv =
mehr Blur, Kamera/Drag = am transparentesten). Technik: CSS `backdrop-filter` (Element muss
teil-transparent sein). → **gestufte Hierarchie statt flächendeckendem Glow.**
[backdrop-filter @ MDN]

**→ Konkret für Universe — die Politur-Hebel:**
1. **Ein** zentrales Komponenten-Set (Button/Card/Chip/Tab/Progress/Modal) als Single Source,
   **keine** Per-Screen-Styles mehr → behebt die Konsistenz-Drift.
2. **Glow/Blur/Glas sparsam & gezielt** (nur Fokus/aktiv/Schlüssel-Overlays), nicht auf jeder
   Karte → genau die Grenze zwischen „cinematic" und „Neon-überladen" (auch Performance-relevant, §5).
3. **Hintergrund beruhigen:** EINE atmosphärische Tiefen-Ebene statt 4 konkurrierender Layer.
4. **Echte Display-Typo** statt System-Font (siehe §8).

---

## 4. Datendichte & Lesbarkeit  ✅ BELEGT

**Erkenntnis (NN/g Mobile Tables):** Bei für Mobile angepassten Tabellen **Header beim vertikalen
Scrollen fixieren** und **linke Label-Spalte beim horizontalen Scrollen sperren**. Bei wortreichen
Einträgen passen nur **~2 Spalten** lesbar; bei **zahlenlastigen** Tabellen (Flotten, Rangliste,
Kampfberichte) mehr. [nngroup.com/articles/mobile-tables]

**→ Konkret für Universe:**
- **Rangliste / Flottenlisten:** Desktop dicht (Tabelle), Mobile = **gestapelte Karten** ODER
  scrollbare Tabelle mit **gesperrter Name/Rang-Spalte + fixem Header**.
- **Zahlen:** durchgängig `font-variant-numeric: tabular-nums` (vorhandene `.mono`-Klasse), Kurz-
  format `1.2M` (vorhandene `ShortNumberPipe`), Raten als `+1.2K/h`. *(Format-Detail = Design­entsch.)*
- **Tile-Raster** (Gebäude/Werft) beibehalten — gutes OGame-Erbe; konsistente Karten-Komponente.

---

## 5. Performance-Leitplanken (CSS-Effekte)  ✅ BELEGT

- **Nur `transform` und `opacity`** sind compositor-only animierbar (kein Layout/Paint) → alle
  Hover/Pulse/Panel-Transitions ausschließlich darüber. Layout-Properties (top/left/width/height)
  lösen Reflow aus und bleiben nicht flüssig. [web.dev/animations-guide]
- **Layer kosten Speicher** (besonders Mobile-GPU); `will-change`/Layer-Promotion **sparsam**.
  `backdrop-filter`/blur sind **teuer** → gezielt auf wenige Schlüssel-Panels, nicht flächendeckend.
  [web.dev/stick-to-compositor-only-properties]
- Das deckt sich 1:1 mit der visuellen Empfehlung „Glas/Glow gezielt" (§3.2).

---

## 6. Accessibility-Leitplanken  ✅ BELEGT

- **Dark-Mode-Kontrast mit APCA (Lc) prüfen, nicht WCAG-2-Ratio** — 4.5:1 kann auf nahezu
  schwarzem Grund funktional unlesbar sein; APCA ist perzeptuell uniform (Lc 60 = gleiche
  wahrgenommene Lesbarkeit hell wie dunkel). *(Caveat: APCA ist WCAG-3-Kandidat, Quelle parteiisch,
  technische Kritik aber unabhängig bestätigt.)* [git.apcacontrast.com/WhyAPCA]
- **Touch-Targets:** WCAG 2.2 AA = min. **24×24px**, Praxis/AAA = **44–48px** (Apple 44pt,
  Material 48dp). → Mobile alle interaktiven Elemente **≥44px**; dichte Desktop-Targets dürfen
  kleiner sein, **nie unter 24px**. [w3.org/WAI/WCAG22 SC 2.5.8]
- **Ressourcen-Farbcodierung farbenblind-sicher:** Farbe nie alleiniger Träger → immer + Icon/Label.

---

## 7. Onboarding & Intuitivität  🎨 DESIGNEMPFEHLUNG (nicht quellen-belegt)

> Die Recherche hat hierzu **keine** ausreichend verifizierten Quellen geliefert — folgendes ist
> begründete Design-Empfehlung, kein belegter Fakt. Optionale Folge-Recherche siehe §10.

- **Geführte FTUE statt Wall-of-Text:** erste Sitzung als kontextuelle Mini-Quest-Kette
  („Baue Metallmine", „Sende erste Spähsonde") mit Hervorhebung des nächsten Klicks.
- **Progressive Disclosure:** fortgeschrittene Screens (Techbaum, Simulator, Kommandeure) erst
  freischalten/hervorheben, wenn relevant — nicht alle 12 Items am Tag 1 gleich laut.
- **Empty States** als Handlungsführung („Noch keine Flotte — hier entsenden") statt leerer Listen.
- **Tooltips/Inline-Hilfe** an Ort und Stelle (vorhandenes `.tip`-Muster ausbauen, konsistent).
- Ziel: OGame-Tiefe **bewahren**, aber den Einstieg geleiten — Tiefe schrittweise enthüllen.

---

## 8. Start-Design-System (Token-Skizze)  🎨 DESIGNENTSCHEIDUNG

> Konkreter Startpunkt, baut auf der vorhandenen Palette auf und schließt die Ist-Lücken aus §1.
> Werte als Vorschlag — im Redesign feinjustierbar; Kontraste final mit APCA prüfen (§6).

**Spacing-Skala (4px-Basis):** `--sp-1:4 · --sp-2:8 · --sp-3:12 · --sp-4:16 · --sp-6:24 ·
--sp-8:32 · --sp-12:48`. Alle Abstände NUR aus dieser Skala.

**Radius:** `--r-sm:6 · --r-md:10 · --r-lg:16 · --r-pill:999`. Die `clip-path`-Schrägecke nur noch
als **sparsamer Signatur-Akzent** (z. B. Modal-Header), nicht auf jedem Panel (= wirkt sonst billig).

**Elevation (statt nur 1 Schatten):**
`--e0:none` · `--e1: 0 1px 2px rgba(0,0,0,.4)` (Karten) · `--e2: 0 8px 24px rgba(0,0,0,.5)` (Pop­over) ·
`--e3: 0 16px 48px rgba(0,0,0,.6)` (Modal). Glow als **eigenes, separates** Fokus-Token, nicht in Elevation gemischt.

**Glow (genau ein Akzent-Token, gezielt):** `--glow-accent: 0 0 16px rgba(46,230,214,.35)` — nur
auf `:focus-visible`, aktiven Tabs, Primär-Button-Hover. Sonst NICHT.

**Motion-Tokens:** `--motion-fast:120ms · --motion-base:200ms · --motion-slow:320ms`;
Easing `--ease-out: cubic-bezier(.2,.8,.2,1)`. Nur `transform`/`opacity` animieren (§5).

**Typografie (Vorschlag — kein Orbitron-Klischee):**
- *Display/Headings:* technische, aber lesbare Sci-Fi-Schrift — **„Space Grotesk"** oder
  **„Rajdhani"/„Saira"** (selbst-gehostet wegen Privacy/Perf).
- *Body/UI:* **„Inter"** (neutral, hochlesbar).
- *Zahlen/Mono:* **„IBM Plex Mono"** o. „JetBrains Mono" mit `tabular-nums`.
- *Type-Scale* (≈1.25): `--fs-xs:12 · sm:13 · base:14/15 · lg:18 · xl:24 · 2xl:32`.

**Farbe/Surfaces (Ramp statt 3 Ad-hoc-Stufen):** dunkle Surface-Treppe `bg-deep → bg → surface-1
→ surface-2 → surface-3` mit klar steigender Helligkeit; **Cyan = primärer Akzent**; **Magenta auf
echte Semantik beschränken** (Gefahr/Feind/„voll"), nicht dekorativ; semantische Tokens
(`--ok/--warn/--danger/--info`) + Ressourcen-Farben (metal/crystal/deuterium/energy) beibehalten,
aber Sättigung zügeln.

**Glas-Panel (3 Zustände, gezielt):** `backdrop-filter: blur(…) saturate(…)` + halbtransparente
Surface — aktiv klar / inaktiv stärker geblurrt / Drag am transparentesten (§3). Nur Overlays/Modals.

---

## 9. Priorisierte Roadmap

**Quick Wins (hoher Effekt, geringer Aufwand):**
1. **Token-Fundament** ergänzen: Spacing-, Elevation-, Radius-, Motion-Skala in `styles.scss`.
2. **Echte Display-Typo** einbinden (self-hosted) + Type-Scale-Tokens.
3. **Hintergrund entrauschen** (eine Tiefen-Ebene statt vier).
4. **Glow/Glas auf gezielt** zurücknehmen (nur Fokus/aktiv/Overlays).
5. **Emoji-Fallbacks** durch ein einheitliches Icon-Set ersetzen.

**Strukturell (höherer Aufwand, höchster Hebel):**
6. **Zentrale Komponentenbibliothek** (Button/Card/Chip/Tab/Progress/Modal) — Per-Screen-Styles
   auf gemeinsame Komponenten migrieren (Konsistenz = Kern des AAA-Looks).
7. **Navigation neu:** gruppierte, kollabierbare Desktop-Sidebar + **Mobile-Bottom-Tab-Bar (5)**;
   doppelten Planetenwechsler auflösen.
8. **Responsive Datenmuster:** Tabellen → Desktop dicht / Mobile Karten bzw. gesperrte Spalte+Header.
9. **Onboarding-Schicht** (FTUE-Questkette, Empty States, progressive Disclosure).
10. **A11y-Pass:** APCA-Kontrast, Fokus-Ringe, Touch-Targets ≥44px mobil.

**Reihenfolge-Empfehlung:** 1–2 (Fundament) → 6 (Komponenten) → 7 (Navigation) als sichtbarer
Sprung → dann 3–5/8/10 (Politur) → 9 (Onboarding) zuletzt.

---

## 10. Offene Fragen / empfohlene Folge-Recherche

Von der Recherche als **nicht belegt** markiert — bei Bedarf gezielt nachrecherchierbar:
1. **Onboarding/FTUE-Muster** für OGame-artige Aufbauspiele (empirisch belegt).
2. **Typografie/Font-Pairings** + belegte Token-Skalen (Spacing/Elevation/Radius/Motion) als Startwerte.
3. **Vergleichs-Fallstudien** Stellaris / Star Trek Fleet Command / Hades' Star (IA + Datendichte).
4. **Zahlenformat & farbenblind-sichere Ressourcen-Codierung** (belegte Konventionen).

---

## Nachtrag (2026-06-13): Folge-Recherche zu den offenen Fragen §10

Eine fokussierte Folge-Recherche zu Onboarding/FTUE, Typo/Token-Skalen, Fallstudien und
Zahlen-/Farbcodierung wurde durchgeführt, konnte die **adversariale Verifikation aber nicht
abschließen** (Session-/Rate-Limit der Verifikations-Agenten). Die gesammelten Quellen-Claims sind
daher *unverifiziert*, decken sich aber mit etablierter Praxis und stützen die getroffenen
Entscheidungen (als Designgrundlage, nicht als formal belegter Fakt):
- **Onboarding:** Learning-by-doing statt Tutorial-Wall; max. ~3 gleichzeitige neue Infos
  (kognitive Last); progressive Disclosure, eine Mechanik nach der anderen, in-context; Empty
  States als Handlungsführung; gesperrte Inhalte sichtbar machen, um Freischaltung zu motivieren
  (Fortnite-HUD); FTUE ist ein direkter Retention-Prädiktor (~20% Drop in der ersten Stunde).
  → Die gebaute Onboarding-Schicht (`OnboardingService` + `onboarding-panel`) folgt dem: ein
  hervorgehobener nächster Schritt mit Aktion, gelatchter Fortschritt, ausblendbar.
- **Typografie:** Space Grotesk (aus Space Mono abgeleitet) als Sci-Fi-taugliche Display-Schrift bestätigt.
- **Motion/Elevation (Carbon/Atlassian):** Dauern ~70–700ms gestaffelt, „productive/expressive"-Easing;
  Dark-Elevation = Surface aufhellen + Schatten (deckt sich mit der Surface-Ramp + `--e1/2/3`).
- **Zahlen:** `Intl.NumberFormat` Compact (`1.2K`/`123M`) + Compound-Units für Raten (locale-korrekt).
- **Farbenblind-sicher:** Farbe nie allein — Icon/Label/Muster zusätzlich; Paletten IBM-Colorblind-Safe / Okabe-Ito.

> Für formale Belegbarkeit kann die Folge-Recherche nach Reset des Limits erneut laufen.

## Quellen (verifiziert, 3-0)
- NN/g: vertical-nav · mobile-navigation-patterns · hamburger-menus · mobile-tables
- EVE/CCP: neo-neocom-1 · improving-photon-ui · a-new-look-for-eves-ui-feedback-needed
- web.dev: animations-guide · stick-to-compositor-only-properties-and-manage-layer-count
- MDN: CSS backdrop-filter · APCA: git.apcacontrast.com/WhyAPCA · W3C WCAG 2.2 SC 2.5.8
