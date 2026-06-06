# Platzhalter-Assets (Stubs)

> **Diese Dateien sind PLATZHALTER, keine finalen Assets.** Sie existieren, damit das
> Frontend sofort etwas Anzeigbares hat, während die echte Asset-Produktion läuft.

Jeder Stub ist ein **selbst generiertes, valides SVG** (keine externen URLs/Abhängigkeiten),
das dem Farbschema und der Form-Signatur aus [`docs/STYLE_BIBLE.md`](../../docs/STYLE_BIBLE.md)
folgt: dunkles Panel, Cyan-Rahmen mit abgeschnittener Ecke oben-rechts, ressourcen-/rang-/
moral-korrekte Farben und ein beschriftetes Glyph (`PLATZHALTER`).

## Inhalt (30 Stubs, repräsentativ je Kategorie)

| Pfad | Anzahl | Maße | Deckt ab |
|------|:---:|------|----------|
| `icons/resources/` | 4 | 64×64 | **alle** Ressourcen: metal, crystal, deuterium, energy |
| `ships/` | 5 | 512×512 | **alle Vertical-Slice-Schiffe**: light/heavy_fighter, cruiser, small_cargo, spy_probe |
| `buildings/` | 9 | 512×512 | Kern-Gebäude inkl. ⭐ command_academy, command_center |
| `defenses/` | 2 | 512×512 | Vertical-Slice-Verteidigung: rocket_launcher, light_laser |
| `commanders/` | 5 | 1024×1024 | **ein Portrait je Rang** (cadet→legend), Rang-Rampe sichtbar |
| `icons/ui/` | 5 | 256×48 / 64×64 | **4 Moral-Bänder** (high/neutral/low/critical) + alert (Angriffswarnung) |

Die Ordnerstruktur **spiegelt die echten Asset-Pfade** (siehe Style Bible §6) — ein Stub
liegt genau dort, wo das finale Asset hingehört.

## Wie ersetzen?

1. Finales Asset gemäß [`docs/ASSETS.md`](../../docs/ASSETS.md) (Motiv, Maße) und
   [`docs/STYLE_BIBLE.md`](../../docs/STYLE_BIBLE.md) (Stil, Prompt-Baukasten) produzieren.
2. Unter dem **gleichen Dateinamen** (= `balance.json`-Key) in den entsprechenden
   **`assets/<kategorie>/`**-Ordner legen — **nicht** mehr unter `placeholders/`.
   Beispiel: `placeholders/ships/cruiser.svg` → final `assets/ships/cruiser.png`.
3. Das Frontend referenziert Assets per Key; sobald das finale Asset im echten Ordner liegt,
   wird der Stub nicht mehr gebraucht. `placeholders/` kann am Ende komplett entfernt werden.

## Regenerieren

Alle Stubs sind reproduzierbar (kein Hand-Editieren nötig):

```bash
node assets/placeholders/_generate.js
```

Der Generator (`_generate.js`) hält die Palette als Single-Source synchron zur Style Bible.
Wer die Platzhalter-Farben ändert, ändert sie dort zentral. (Ursprünglich Python-geplant;
auf Node umgestellt, da in der Build-Umgebung verfügbar.)

## Was hier (noch) fehlt — bewusst

Spätere/„L"-Assets (Schlachtschiff, Todesstern, restliche Verteidigung, Hintergründe,
Effekte, vollständiges Commander-Layer-System, UI-Buttons/Panels) sind in `ASSETS.md`
spezifiziert, aber **nicht** als Stub erzeugt — sie blocken den Vertical Slice nicht.
Bei Bedarf den Generator um weitere Einträge erweitern.
</content>
