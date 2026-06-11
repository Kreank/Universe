# 03d — Kampf-Redesign: Rapidfire-Abschaffung & Rollen als Rückgrat

> **Status:** ENTWURF zur Abnahme (Stand 2026-06-11). Gemeinsam erarbeitet (Nutzer + Claude).
> Ersetzt die Rapidfire-Philosophie aus `03a`/`03b` teilweise. Quelle der Wahrheit für den
> anstehenden Umbau von `shared/balance.json` (+ kleine Engine-Anpassungen).
> Bezug: `03b-role-based-combat.md` (Subsysteme/Reichweite), `03c-role-roster-spec.md` (Roster),
> `08-moons-and-warfare-buildings.md` (Monde), `backend/app/combat/engine.py`.

---

## 1. Motivation — warum wir Rapidfire abschaffen

OGames Rapidfire ist über die Jahre zur Monokultur degeneriert: irgendwann bestanden Flotten
nur noch aus Schlachtkreuzern/Schlachtschiffen, Speed-Flotten nur aus Kreuzern — wer das
kosteneffizienteste Rapidfire-Schiff in Masse stellte, mähte alles nieder. Vielfalt kollabierte.

**Mechanische Ursache (in dieser Engine verifiziert, `engine.py:fire`):**
- **Overkill verpufft:** Ein Schuss trifft genau **ein** Ziel; Restschaden über die Hülle hinaus
  ist verloren. Das ist die **natürliche Anti-Masse-Bremse** — ein 2.200-Schaden-Zerstörer auf
  einen 400-Hülle-Jäger verschwendet ~1.800.
- **Rapidfire hebelt genau diese Bremse aus:** Nach einem Treffer feuert die Einheit sofort auf
  ein *frisches* Ziel → kein verpuffter Schaden, linearer Massen-Skalierung. **Universelles
  Rapidfire = abgeschaltete Anti-Masse-Bremse = OGame-Degeneration.**

**Konsequenz:** Schiff-vs-Schiff-Rapidfire wird **komplett gestrichen**. Die Overkill-Bremse
bleibt erhalten und erzwingt, dass Masse einer Einheit ineffizient wird.

---

## 2. Kernprinzipien

1. **Kein Schiff-gegen-Schiff-Rapidfire.** Punkt.
2. **Rückgrat = Schadenstyp-Matrix × Subsystem + Reichweiten-Bänder + Overkill-Bremse + Rollen-
   Mechaniken.** Daraus entsteht das Schere-Stein-Papier, nicht aus Rapidfire.
3. **Rapidfire überlebt NUR als Anti-Verteidigung** (siehe §4) — weil Verteidigung ein anderes
   Tier ist (stationär, billig, in Masse spambar, Schild-Regen pro Runde) und die Subsystem-Matrix
   „Anti-Gebäude" gar nicht ausdrücken kann.
4. **Rollenschiffe tragen die Spezial-Mechaniken** (Ionen-Lähmen, Entern, Tarnkappe-Hinterhalt,
   Drohnen, Punktverteidigung) — nicht Rapidfire.
5. **Balance über Kosten + Bauvoraussetzungen** (Forschung **und** Werft-Stufe), nicht über
   dominante Rapidfire-Platformen.

---

## 3. Das Rückgrat: Schadenstyp × Subsystem

Aktuelle Matrix (`combat.damage_matrix`, Effektivität gegen {Schild, Antrieb, Hülle}):

| Waffentyp | Schild | Antrieb | Hülle | Rolle |
|-----------|--------|---------|-------|-------|
| energy    | 1.5    | 0.5     | 0.6   | **strippt Schilde**, schwach gegen Hülle |
| kinetic   | 0.25   | 0.75    | 1.3   | **zerlegt Hüllen**, prallt an Schilden ab |
| missile   | 0.5    | 0.7     | 1.2   | Anti-Hülle, mittel gegen Schild |
| ion       | 1.4    | 1.6     | 0.0   | **lähmt** (Schild+Antrieb), tötet NICHT |

**Der gewollte Kreislauf (kombinierte Waffen):**
`Energie strippt Schild → Kinetik/Rakete zerlegt Hülle → Ionen lähmt (Mission-Kill/Capture)`.
Eine Mono-Flotte hat immer ein Loch: reine Kinetik zerschellt an Schilden (0.25), reine Energie
kriegt Hüllen nicht klein (0.6), reine Ionen tötet nie (0.0).

**Tuning-Absicht:** Der `_note` in balance.json gesteht, dass **Kinetik-vs-Schild 0.25 ein Notnagel**
war („bis Ionen-/Schild-Strip-Schiffe existieren"). Die existieren jetzt (EWAR-Fregatte). Damit
können wir Kinetik-vs-Schild Richtung **0.1–0.0** schärfen → Schilde werden zur echten Mauer, die
**Energie/Ionen** brechen muss. Genauer Wert: Phase 1, nach Sim-Tests.

**Reichweiten-Bänder** (`combat.range_bands`): Distanz schließt sich `far → medium → near`
(1 Band/Runde). Ein Schiff feuert nur ab seiner Reichweite; näher als optimal → Standoff-Strafe
(0.5/Band). Das ist der zweite Rückgrat-Pfeiler: Fern-Artillerie (Zerstörer) schlägt zuerst, ist
aber im Nahkampf schwach → schnelle Schiffe, die die Distanz schließen, kontern sie.

---

## 4. Rapidfire — die EINZIGE überlebende Anwendung: Anti-Verteidigung

Verteidigung ist stationär + billig + Schild-Regen pro Runde + in Masse spambar. Ohne Anti-
Verteidigungs-Mechanik wird **Verteidigungs-Spam degeneriert**: 1.000 billige Raketenwerfer
(~100 Kosten) saugen das gegnerische Feuer im Overkill auf — eine Wegwerf-Mauer. Die Subsystem-
Matrix kann „Anti-Gebäude" nicht ausdrücken (Verteidigung hat Schild/Hülle wie Schiffe).

**Lösung — zwei Rollen, kein universelles Rapidfire:**
- **Bomber → Rapidfire gegen Verteidigung.** Durchkettet die Turm-Mauer statt im Overkill zu
  verpuffen. Das ist die *einzige* verbleibende Rapidfire-Tabelle im Spiel. (Werte: Phase 1.)
- **EWAR-Fregatte → Ionen lähmt Verteidigung** (`combat.defense_disable` existiert bereits) —
  Geschütze feuern nicht mehr.

Anti-Verteidigung = **Bomber (durchketten) + EWAR (lähmen)**. Sonst hat keine Einheit Rapidfire.

---

## 5. Linienschiffe (Rückgrat-Roster)

Kein Rapidfire. Balance über Waffentyp, Reichweite, Stats, Kosten. Profil-Skizze (Werte = Phase 2):

| Schiff | Waffe | Reichweite | Profil / Rolle |
|--------|-------|-----------|----------------|
| Leichter Jäger | kinetic | nah | billige Masse, Anti-Hülle; stirbt schnell |
| Schwerer Jäger | kinetic | nah | robustere Masse |
| Kreuzer | energy | mittel | **Schild-Stripper**, schnell; bricht gegnerische Schilde |
| Schlachtschiff | kinetic | mittel | Arbeitspferd, solide Hülle/Schaden |
| Schlachtkreuzer | kinetic | mittel | **Tank** (Schild 400/Hülle 7.000), zäher Brecher |
| **Zerstörer** | kinetic | **fern** | **GLASKANONE** — siehe §6 |

**Wichtig:** Wer welche Klasse „schlägt" ergibt sich aus Waffentyp×Panzerung + Reichweite +
Overkill, **nicht** aus einer Rapidfire-Leiter. Beispiel: Eine reine Kreuzer-Speedflotte (energy)
strippt zwar Schilde, zerlegt aber Hüllen kaum (0.6) → braucht Kinetik-Begleitung.

---

## 6. Zerstörer-Entscheidung — EMPFEHLUNG: Glaskanone

**Aktuelle Werte:** Angriff 2.200 (höchster!), Schild 120 (niedrig), Hülle 3.500 (mittel —
*weniger* als Schlachtschiff 6.000 / Schlachtkreuzer 7.000), Speed 5.000 (langsamster).
→ Faktisch schon eine **langsame Fern-Glaskanone**, kein Tank.

**Empfehlung Glaskanone (statt OGame-Tank), Begründung:**
1. Der **Tank-Platz ist besetzt** (Schlachtkreuzer/Träger sind die Dickschiffe) — ein Tank-
   Zerstörer wäre charakterlose Dublette.
2. Das System lebt von **ausnutzbaren Schwächen**: Fern-Alpha + dünn + langsam → schnelle Schiffe
   (Abfangjäger/Tarnkappe) schließen über die Reichweiten-Bänder die Distanz und zerlegen die
   Hülle. **Emergenter, intuitiver Konter statt hartkodiertem Rapidfire.**
3. **Overkill diszipliniert sie:** will auf Großkampfschiffe zielen, nicht auf Jäger.
4. Eigene Nische (Capital-Sniper, **braucht Eskorte** = kombinierte Waffen) und **nicht von OGame
   abgekupfert.**

**Tuning-Wächter:** Alpha darf nicht „Runde 1 entscheidet alles" werden — Reichweiten-Schließung
gibt dem Gegner Runden zum Herankommen; ggf. Angriff leicht senken, Hülle/Schild bewusst dünn lassen.

> **OFFEN:** Nutzer-Entscheidung Glaskanone (empfohlen) vs. Tank. Bei Tank: Schild/Hülle hoch,
> Angriff runter, andere Nische.

---

## 7. Todesstern-Redesign (Star-Wars-Stimmigkeit)

Der Todesstern ist **keine Kampfflotten-Mähmaschine** mehr. Seine Rollen:

1. **Belagerungswaffe — Mondzerstörung (NEUE Mechanik, existiert noch nicht).**
   Ein Todesstern im Angriff würfelt auf Zerstörung des Ziel-**Monds**. Chance skaliert mit
   **Mondgröße (Felder)** + **Anzahl Todessterne**, plus **Rückschlag-Risiko** (der Todesstern
   kann beim Versuch selbst zerstört werden — OGame-stimmig). Mit dem Mond fallen Sprungtor/
   Phalanx/Orbitalbatterie. (Planeten selbst sind unzerstörbar — bewusst, sonst zu krass.)
2. **Drohnenträger.** Wie der Träger lädt er beim Angriff Drohnen aus der Garnison —
   **Kapazität 50** (Träger: 8), per Forschung auf **bis 100** erhöhbar. Die Drohnen kämpfen,
   nicht der Todesstern.
3. **Kein Schiff-Kampf-Wert von Bedeutung.** Ohne Rapidfire verpufft sein Riesen-Schaden im
   Overkill (1 Schiff/Runde) → er ist **allein nicht überlebensfähig**, braucht Eskorte + seine
   Drohnen. Langsamster im Spiel (Speed 100).

**Engine-Bedarf:** (a) Träger-Beladung in `send_fleet` von „nur `carrier`" auf **Kapazität pro
Schiffstyp** verallgemeinern (`carrier: 8`, `deathstar: 50`); (b) Forschungseffekt „Todesstern-
Drohnenkapazität → 100"; (c) Mondzerstörungs-Phase im Angriffs-Resolve.

> **OFFEN:** genaue Drohnen-Kapazität (50 Start / 100 max?), Mondzerstörungs-Chance-Formel,
> Rückschlag-Wahrscheinlichkeit.

---

## 8. Rollenschiffe — Spezial-Mechaniken (kein Rapidfire außer Bomber)

Stärke = Effekt, nicht Rapidfire. Alle sind über die Matrix/Reichweite **konterbar**.

| Rollenschiff | Mechanik (Engine-Flag/Waffe) |
|--------------|------------------------------|
| EWAR-Fregatte | **Ionen** (lähmt Antrieb+Schild von Capitals, lähmt Verteidigung) |
| Bomber | **Rapidfire vs Verteidigung** (einzige Rapidfire-Ausnahme) |
| Abfangjäger | schnell, nah — Anti-Jäger über Tempo/Reichweite, **kein** RF |
| Tarnkappe-Korvette | **Hinterhalt** (Überraschungsrunde, `stealth`) |
| Boarder | **Entern** gestrandeter Schiffe (`boarder`) |
| Interdiktor | **Interdiktion** (verhindert Disengage/Fleetsave) |
| Schild-Tender | **Schild-Projektor** (Support, 0 Angriff) |
| Träger | **Drohnenträger** (Kapazität 8) |

---

## 9. Kosten & Bauvoraussetzungen

**Problem (verifiziert):** Wenige Antriebs-Techs gaten fast alles — `impulse_drive` schaltet **9**
Schiffe frei, `combustion_drive` 7, `hyperspace_drive` 6. → Freischaltungen sind nicht verteilt.

**Maßnahmen:**
1. **Werft-Stufe als Bauvoraussetzung** je Schiff (`requires: { shipyard: N, ... }`). ✅ **kein
   Backend-Code nötig** — `_requirements_met` (`buildings/shipyard.py`) prüft generisch Forschung
   *oder* Gebäude-Stufe; das Popup zeigt's bereits als Voraussetzung an.
2. **Freischaltungen verteilen:** Schiffe über mehr Techs **und** Werft-Stufen staffeln, statt 9
   an einer Tech. Faustregel: pro Tech 1–3 Schiffe, gestaffelte Werft-Stufen als zweite Achse.
3. **Kosten an die (neue) Stärke koppeln** — stärkere/spezialisiertere Rollenschiffe müssen
   entsprechend teurer/voraussetzungsreicher sein, sonst Auto-Pick. (Werte: Phase 2.)

---

## 10. Sonderfall Chaff: Solarsatellit / Spionagesonde

0-Angriff-Einheiten waren bisher per Rapidfire schnell weggeräumt. Ohne Schiff-Rapidfire werden
sie zu **Overkill-Schwämmen** (v.a. Solarsatelliten stehen stationär auf verteidigten Planeten).
**Vorschlag:** Solarsatellit als „verteidigungs-artig" behandeln → vom Anti-Verteidigungs-
Rapidfire (Bomber) mit erfasst, ODER ihm ~0 effektive Hülle geben, sodass er trivial stirbt.

> **OFFEN:** Behandlung Solarsatellit/Sonde festlegen.

---

## 11. Offene Punkte (Nutzer-Entscheidungen)

- [ ] Zerstörer: **Glaskanone** (empfohlen) vs. Tank.
- [ ] Kinetik-vs-Schild-Zielwert (0.1? 0.0?).
- [ ] Todesstern: Drohnen-Start/Max (50/100?), Mondzerstörungs-Formel + Rückschlag.
- [ ] Solarsatellit/Sonde-Behandlung.
- [ ] Bomber→Verteidigung-Rapidfire-Werte; Verteilung der Freischaltungen; Kosten-Tabelle.

---

## 12. Umsetzung in Phasen

1. **Rapidfire raus + Matrix** — alle Schiff-vs-Schiff-`rapidfire` entfernen (nur Bomber→
   Verteidigung bleibt); Kinetik-vs-Schild schärfen. Sim-/Test-Lauf. *Reine balance.json.*
2. **Stats & Kosten** — Linienschiff-Profile (inkl. Zerstörer-Entscheidung) + Kosten-Pass.
3. **Gating** — Werft-Stufen-Voraussetzungen + Freischaltungs-Verteilung.
4. **Todesstern-Mechaniken** — Träger-Beladung verallgemeinern + Drohnen-Forschung +
   Mondzerstörung (Engine). *Backend.*

Verifikation je Phase: `pytest` (124 grün halten) + Kampf-Simulator + Live-Smoke.
