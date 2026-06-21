#!/usr/bin/env bash
# Universe deployen und anschliessend die Aenderungen auf Discord ankuendigen.
#
# Baut die Code-Services neu, startet den Stack und postet danach automatisch
# spielerfreundliche Patch-Notes (KI-umformuliert) in den Discord-Channel.
#
#   ./infra/deploy.sh              # voller Deploy + Ankuendigung
#   ANNOUNCE=0 ./infra/deploy.sh   # deployen, aber nichts ankuendigen
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/infra"

echo "==> Baue Code-Images (game-server, ai-worker, frontend) …"
docker compose build game-server ai-worker frontend

echo "==> Starte/aktualisiere Stack …"
docker compose up -d

if [[ "${ANNOUNCE:-1}" == "1" ]]; then
    echo "==> Kuendige Aenderungen auf Discord an …"
    # Best-effort: ein fehlgeschlagener Post darf den Deploy nicht rot faerben.
    python3 "$ROOT/scripts/announce_discord.py" || \
        echo "!! Ankuendigung fehlgeschlagen (Deploy ist trotzdem durch)." >&2
fi

echo "==> Fertig."
