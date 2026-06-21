# Universe — Agenten-Leitfaden

Browserbasiertes Weltraum-Aufbau-MMO. Server-Pfad: `/srv/storage/projects/universe`.
Live: `universe.tech-artist.de`. Branch `main`, Remote `github.com:Kreank/Universe`.

Diese Datei wird automatisch in jeden Agenten-Kontext geladen. Ausführliche
Übergabe + Verifikations-Loop-Eigenheiten: siehe `HANDOFF.md`.

## ‼️ Deployen — IMMER über `./infra/deploy.sh`

Jede KI, die das Spiel deployt, MUSS dafür das Wrapper-Skript benutzen:

```bash
./infra/deploy.sh
```

Es baut die Code-Images (`game-server`, `ai-worker`, `frontend`), startet den
Stack (`docker compose up -d`) und **kündigt die Änderungen anschließend
automatisch auf Discord an** (KI-umformulierte deutsche Patch-Notes via Ollama,
gepostet über den Webhook in `infra/.env` → `DISCORD_WEBHOOK_URL`).

- **Nicht** von Hand `docker compose build … && up -d` deployen — dann unterbleibt
  die Ankündigung. Das Skript ist der einzige vorgesehene Deploy-Weg.
- Deploy ohne Ankündigung (z. B. reiner Restart/Test): `ANNOUNCE=0 ./infra/deploy.sh`.
- Die Ankündigung ist best-effort: schlägt sie fehl, ist der Deploy trotzdem durch.

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
