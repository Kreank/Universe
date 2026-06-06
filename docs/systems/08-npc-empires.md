# System-Design: NPC-Imperien & PvE

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](../GAME_DESIGN_DOCUMENT.md)
> · setzt GDD §10.2 um · koppelt an [06 Universum](./06-universe-and-map.md), [04 Kampf](./04-combat-model.md)
>
> KI-gesteuerte Fraktionen, die das persistente Universum lebendig halten. **Verhalten läuft
> über Behavior Trees / Utility-AI — kein LLM** (skaliert auf Tausende, GDD §10.2). LLM nur
> bei *direkter Diplomatie mit einem Spieler*. ⭐ = Universe-spezifisch.

---

## 1. Warum NPCs zentral sind

Ohne Resets (GDD §7) braucht die Karte dauerhaft Leben und die Neulinge brauchen Gegner,
die **nicht** Veteranen sind. NPCs lösen mehrere Designziele auf einmal:

1. **Karte beleben** — Frontier & Leerräume wirken nie tot (GDD §7.1).
2. **PvE-Onramp** — Neulinge üben Kampf an NPCs statt von Veteranen gefarmt zu werden
   (stützt Anti-Bashing, GDD §8).
3. **Wirtschafts-Liquidität** — Händler-NPCs sorgen für Markt & Handel auch bei wenig
   Spielern in der Nähe.
4. **Commander-Quelle** — Piraten-Commander gefangen nehmen/abwerben (GDD §6.6).

---

## 2. NPC-Typen

| Typ | Rolle |
|-----|-------|
| **NPC-Imperien** | „echte" Reiche, die bauen, expandieren, verteidigen und gelegentlich raiden. Besiedeln Frontier/Leerraum. |
| **Piratenfraktionen** ⭐ | aggressive Räuber: PvE-Bedrohung *und* lohnende Angriffsziele; Quelle für gefangene Commander & Beute. |
| **Händler-NPCs** | Markt-Liquidität, Handelsrouten, „Kantine" zum **Anwerben** von Commandern (Doku 01/05). |
| **Neutrale Außenposten** | Quest-/Missions-Hubs, Begegnungen, Lore-Anker (auch via Expeditionen, Doku 07). |

---

## 3. KI-Ansatz (kein LLM fürs Verhalten)

- **Utility-AI / Behavior Trees:** NPCs bewerten Optionen (expandieren, bauen, angreifen,
  handeln, verteidigen) nach gewichteten Kriterien und handeln regelbasiert. Billig,
  deterministisch genug, skaliert massiv.
- **Verhaltensprofile (Parameter-Sets):** z. B. *expansiv, aggressiv, defensiv, händlerisch* —
  steuern Gewichtung. Ein Piraten-Profil raidet; ein Händler-Profil meidet Kampf.
- **Tick-Einbindung:** NPC-Aktionen laufen über denselben geplanten Ereignis-/Cron-Mechanismus
  wie die Spielwirtschaft (Architektur §6), nicht in Echtzeit pro Sekunde.
- **LLM nur bei Spieler-Diplomatie:** Bündnisangebot, Drohung, Lösegeld-Verhandlung mit
  *einem* Spieler → seltener Großmoment-Job an den AI-Worker (Architektur §5.4, GDD §10.2).

---

## 4. Schwierigkeits- & Regionen-Skalierung ⭐

Koppelt an das Regionen-Ring-Modell (Doku 06 §6):

- **Frontier:** schwächere, zahlreichere NPCs → sanfter PvE-Einstieg für Neulinge.
- **Kern:** stärkere, seltenere, lohnendere NPCs → echte Herausforderung & Belohnung.
- **Adaptive Note (leichtgewichtig):** NPC-Stärke/-Häufigkeit kann grob an das lokale
  Spielerniveau angepasst werden (Teil der „Adaptive Balance", GDD §10.4) — ohne schweres
  ML, nur über Telemetrie-Schwellen.

---

## 5. Anti-Farming & Ökonomie-Hygiene ⭐

NPCs dürfen keine unendliche Gratis-Beutequelle sein (sonst kippt die Wirtschaft):

- **Eskalierende Verteidigung / Cooldowns:** wiederholtes Farmen desselben NPC lohnt
  abnehmend; NPC verstärkt sich oder verlegt sich.
- **Begrenzte Beute-/Commander-Drops:** seltene Belohnungen (z. B. gefangener
  Elite-Commander) mit echten Bedingungen, nicht beliebig wiederholbar.
- **Piraten-Vergeltung:** zu aggressives Piraten-Farmen kann Gegen-Raids auslösen → Risiko.

---

## 6. Tuning-Hebel & offene Entscheidungen 🔧

1. **PvE-Stellenwert:** ✅ **Entscheidung (2026-06-06): reiche PvE-Ebene** — Fraktionen mit
   Reputation, NPC-Quests, eigene Progression. Dauerhafter Inhalt & sanfter Einstieg für
   Solo-/Casual-Spieler (stützt Casual-Bindung & Anti-Bashing). Umfang ggf. gestaffelt
   ausrollen (erst Kern-PvE, dann Reputation/Quests).
2. **Dynamik der NPC-Imperien:** ✅ **Entscheidung (2026-06-06): voll dynamisch** — sie
   expandieren wirklich, konkurrieren um Raum und können Spieler angreifen. Lebendigste
   Welt; erfordert sorgfältiges Balancing (Frontier-Schonung für Neulinge, GDD §8).
3. **Profil-Gewichte, Spawn-Dichten je Region, Eskalations-/Cooldown-Werte, Drop-Raten,
   adaptive Schwellen** → Prototyp.

---

## 7. Abhängigkeiten zu anderen System-Dokus

- **06 Universum** — Besiedlung von Frontier/Leerraum, Regionen-Skalierung.
- **04 Kampf** — NPC-Flotten/Verteidigung, gefangene Commander.
- **01 Wirtschaft / Handel** — Markt-Liquidität, Anwerbe-„Kantine".
- **05 Commander** — Piraten-/Anwerbe-Commander, Loyalität Umgedrehter.
- **07 Missionen** — Expeditions-Begegnungen, Angriffsziele.
- **GDD §10.2/§10.4** — KI-Verhalten ohne LLM, adaptive Balance; **§8** Anti-Bashing/PvE-Onramp.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. NPC-Typen (Imperien/Piraten/Händler/Außenposten),
  KI-Ansatz (Behavior Trees, kein LLM; LLM nur Spieler-Diplomatie), Regionen-/Schwierigkeits-
  Skalierung, Anti-Farming, Tuning-Hebel (PvE-Stellenwert, NPC-Dynamik).
