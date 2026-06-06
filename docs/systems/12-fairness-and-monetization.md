# System-Design: Fairness & Monetarisierung

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · setzt Querschnittsziele aus GDD §8 & Doku 01/10 um
>
> Wie sich das Spiel finanziert — **ohne Pay-to-Win** — und wie Fairness technisch &
> regelseitig gesichert wird (Anti-Cheat, Multi-Account, Pushing, Bots). ⭐ = Universe-spezifisch.

---

## 1. Grundprinzip

**Premium darf Komfort, Zeit und Aussehen geben — niemals rohe Macht.** Das ist
nicht-verhandelbar (GDD-Säule 2/3, Doku 01 §1, Doku 10 §4). Ein zahlender Spieler soll
*bequemer* und *hübscher* spielen, aber gegen einen gleich aktiven Gratis-Spieler **keinen
Kampf-/Wirtschaftsvorteil** haben.

---

## 2. Monetarisierungs-Modell (F2P)

**Premium-Währung (Arbeitsname „Dunkle Materie"):**
- **kaufbar** mit Echtgeld **und ⭐ ingame verdienbar** (v. a. via **Expeditionen**, Doku 07;
  Belohnungen, Saison-Ziele) → Gratis-Spieler haben Zugang, nur langsamer. Wichtigster
  Fairness-Hebel.

**Was Premium darf (Komfort/Kosmetik/Zeit-Flexibilität):**
- **Kosmetik:** Schiffs-Skins, Commander-Porträts/-Stimmen, Allianz-Embleme, Profil-Flair.
- **⭐ Commander-Flavor:** *mehr/tiefere* Funksprüche & Lore für die eigene Crew, kosmetische
  Persona-Optionen — pure Immersion, **kein** Stat-Vorteil. (Hilft zugleich, die LLM-Kosten
  zu tragen, GDD §10.)
- **QoL:** zusätzliche Bau-Queue-Slots, Flotten-Vorlagen, erweiterte Übersichten, Komfort-
  Shortcuts.
- **Moderate Zeit-Flexibilität** mit **Deckel:** begrenzte Bau-/Forschungs-Beschleunigung,
  klar gekappt, damit kein dauerhafter Macht-Vorsprung entsteht.

**Was Premium NICHT darf (harte Grenze):**
- keine direkten **Kampfwerte**, keine besseren **Commander/Traits**, keine kaufbaren
  Ressourcen-/Flotten-Mengen, die freie Spieler nicht erreichen können, kein Umgehen von
  Span-of-Control, Moral oder Permadeath.

> 🔧 **Fork:** rein **Kosmetik + QoL** (maximal fair, geringere Einnahmen) vs.
> **Kosmetik + QoL + gedeckelte Zeit-Beschleunigung** (mehr Einnahmen, minimaler Komfort-
> Edge). → §6.

---

## 3. Anti-Cheat (technisch)

- **Autoritativer Server** (Architektur ADR-006): alle Regeln/Validierungen serverseitig →
  Client-seitige Manipulation wirkungslos.
- **Reproduzierbare Kämpfe** (Seed, Doku 04) → nachprüfbare Berichte, keine gefälschten Ausgänge.
- **Rate-Limits & Plausibilitätsprüfungen** auf Aktionen (verhindert Skript-Spam/Exploits).

---

## 4. Multi-Account, Pushing & Sitting (Regeln)

Das klassische Genre-Problem: Zweit-Accounts, die einen Haupt-Account mit Ressourcen
„pushen", oder als wehrlose Farmen dienen.

- **Pushing-Schutz:** Begrenzung von **einseitigen Transfers/Handel** zwischen Accounts
  (insb. gleiche IP/Geräte) — Ressourcen müssen ungefähr ausgeglichen fließen.
- **Multi-Account-Politik:** klare Regel, ob mehrere Accounts pro Person erlaubt sind und
  unter welchen Auflagen (kein Interagieren miteinander). ⬅ *Fork §6*
- **Sitting/Urlaubsvertretung:** jemand darf einen Account *verwalten* (z. B. Bau-Queues),
  aber **keine Flotten starten/angreifen** — klassische, faire Sitting-Regel.
- **Account-Sharing** ansonsten untersagt (Sicherheit & Fairness).

---

## 5. ⭐ KI-gestützte Fairness-Telemetrie

Die „Adaptive Balance"-Ebene (GDD §10.4) dient auch der Fairness:

- **Mustererkennung** (regelbasiert/Telemetrie, kein schweres ML): markiert verdächtige
  Muster — einseitiges Pushing, Bot-artige Aktivität (24/7-Präzision), koordinierter
  Multi-Account-Missbrauch — zur **menschlichen Prüfung** (kein Auto-Bann ohne Review).
- **Bot-Abwehr:** gelegentliche Verifikation bei auffälligem Verhalten; serverseitige
  Aktions-Plausibilität.
- Greift mit dem **diegetischen** Anti-Bashing (GDD §8) zusammen: Fairness ist Teil des
  Designs, nicht nur Moderation.

---

## 6. Tuning-Hebel & offene Entscheidungen 🔧

1. **Monetarisierungs-Umfang:** ✅ **Entscheidung (2026-06-06): Kosmetik + QoL + gedeckelte
   Zeit-Beschleunigung.** Tragfähigere Einnahmen bei minimalem Komfort-Edge; harte Grenze
   „kein P2W" bleibt. Konkrete Deckel → Prototyp/Live.
2. **Multi-Account-Politik:** ✅ **Entscheidung (2026-06-06): tolerant + strenge
   Anti-Pushing-Regeln.** Alts erlaubt, dürfen aber nicht miteinander interagieren/pushen
   (harte Transfer-Limits, Erkennung). Praktikabel & durchsetzbar.
3. **Konkrete Transfer-Limits, Beschleunigungs-Deckel, Premium-Preise, Verdienraten der
   Premium-Währung, Bot-Schwellen** → Prototyp/Live-Beobachtung.

---

## 7. Datenschutz-Hinweis (LLM)

Commander-Funksprüche nutzen Spiel-Kontext (Siege, Planeten, Events) — **keine sensiblen
personenbezogenen Daten**. Persona-/Bank-Generierung läuft lokal (Ollama) bzw. mit
Spieldaten, nicht mit privaten Nutzerdaten. Bei späterem Cloud-LLM-Fallback (Architektur §8)
nur Spielkontext senden.

---

## 8. Abhängigkeiten zu anderen System-Dokus

- **01 Wirtschaft / 10 Progression** — „kein P2W", Status-statt-Macht-Belohnungen.
- **07 Missionen** — Expeditionen als Verdienquelle der Premium-Währung.
- **Architektur §3/§8 (ADR-006)** — autoritativer Server, Cloud-LLM-Fallback-Datenschutz.
- **GDD §8/§10.4** — Anti-Bashing, adaptive Balance/Telemetrie.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. F2P-Modell ohne P2W (Premium = Kosmetik/QoL/Zeit-
  Flexibilität, Währung auch ingame verdienbar), harte Grenzen, Anti-Cheat (autoritativer
  Server), Multi-Account/Pushing/Sitting-Regeln, ⭐ KI-Fairness-Telemetrie, Datenschutz,
  Tuning-Hebel (Monetarisierungs-Umfang, Multi-Account-Politik).
