# Universe — Agenten-Leitfaden

Browserbasiertes Weltraum-Aufbau-MMO. Server-Pfad: `/srv/storage/projects/universe`.
Live: `universe.tech-artist.de`. Branch `main`, Remote `github.com:Kreank/Universe`.

Diese Datei wird automatisch in jeden Agenten-Kontext geladen. Ausführliche
Übergabe + Verifikations-Loop-Eigenheiten: siehe `HANDOFF.md`.

## ‼️ Discord-Ankündigung läuft automatisch beim **Commit**

Spiel-Updates werden **automatisch auf Discord angekündigt** — ausgelöst vom
versionierten **`post-commit`-Git-Hook** (`.githooks/post-commit`, aktiv via
`core.hooksPath`). Nach jedem Commit postet er im Hintergrund (best-effort,
blockiert den Commit nie) die neuen spielrelevanten Commits als KI-umformulierte
deutsche Patch-Notes (Ollama `qwen3.5:9b` → Discord-Webhook in `infra/.env` →
`DISCORD_WEBHOOK_URL`). Log: `scripts/.announce.log`.

**Du musst dafür nichts extra tun — einfach normal committen.** Es gibt aber
zwei Regeln, damit tatsächlich etwas (Sinnvolles) gepostet wird:

1. **Commit-Messages im `feat/fix/balance/asset/perf(scope): …`-Format.** Nur diese
   Präfixe werden angekündigt (chore/docs/test/refactor werden bewusst gefiltert).
   Eine Commit-Message OHNE solches Präfix → es wird NICHTS gepostet.
2. **Keine riesigen Sammel-Commits.** Viele kleine, sauber betitelte Commits = schöne
   Patch-Notes. Ein Sammel-Commit `Universe: alles Mögliche` wird weggefiltert und
   muss dann **manuell** angekündigt werden:
   ```bash
   python3 scripts/announce_discord.py --message "…deine Patch-Notes…" \
       --title "🚀 Universe — Großes Update"
   ```

Weitere manuelle Befehle: `--dry-run` (Vorschau), `--since REF`, `--no-ai`.
`./infra/deploy.sh` (build + up -d) ruft die Ankündigung ebenfalls auf — durch den
Commit-Hook ist das aber redundant; der State-Marker (`scripts/.announce_state`)
verhindert Doppel-Posts.

### Wie die Ankündigung funktioniert
`scripts/announce_discord.py` (stdlib-only, läuft auf dem Host) liest die neuen
Commits seit der letzten Ankündigung (Marker `scripts/.announce_state`), filtert
auf spielrelevante Typen (`feat/fix/balance/asset/perf`), lässt **Ollama
`qwen3.5:9b`** spielerfreundliche Patch-Notes daraus formulieren und postet sie
als Discord-Embed. Fällt Ollama aus, gehen die rohen Commits raus.

- Manuell ankündigen: `python3 scripts/announce_discord.py`
- Vorschau ohne Posten: `python3 scripts/announce_discord.py --dry-run`
- Sonderansage (Freitext, ohne KI): `python3 scripts/announce_discord.py --message "Wartung 20 Uhr"`

→ Gute, aussagekräftige Commit-Messages im `feat/fix/balance(scope): …`-Format
sind damit direkt die Quelle der Patch-Notes. Sauber committen lohnt sich.

## Deploy-Topologie
Entwicklung **und** Betrieb laufen auf diesem Server; gebaut wird aus dem lokalen
Stand. Der Server ist die Quelle der Wahrheit (oft `main` *vor* `origin/main`).
**Kein `git pull`-Deploy** — das würde den älteren Remote-Stand über lokale,
noch nicht gepushte Commits mischen.

## Arbeitsweise
- **Testphase aktiv** (externe Tester): Feature-Ideen/Feedback ERST mit Sascha
  abstimmen + Freigabe abwarten; nur klare Bugs proaktiv fixen.
- Nach Backend-/Worker-Code-Änderung erst das Image neu bauen, sonst läuft alles
  gegen den alten Stand (Details + Test-Loop in `HANDOFF.md`).
