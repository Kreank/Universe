#!/usr/bin/env python3
"""Spiel-Updates als Discord-Patchnotes ankuendigen.

Holt die neuen Commits seit der letzten Ankuendigung, laesst Ollama daraus
spielerfreundliche deutsche Patch-Notes formulieren und postet sie via
Discord-Webhook als Embed.

Robustheit (analog ADR-003 des ai-worker): Ollama ist *Veredelung*. Faellt es
aus oder liefert Unsinn, werden die gefilterten Commit-Zeilen direkt gepostet,
damit die Ankuendigung trotzdem rausgeht.

Nur Standardbibliothek -> laeuft direkt auf dem Host ohne venv/pip.

Beispiele:
    python3 scripts/announce_discord.py                 # neue Aenderungen seit letzter Ankuendigung
    python3 scripts/announce_discord.py --dry-run       # nur anzeigen, nichts posten
    python3 scripts/announce_discord.py --since v1.2    # ab einem Git-Ref/Tag/SHA
    python3 scripts/announce_discord.py --message "Wartung heute 20 Uhr"   # Freitext (ohne Git/KI)
    python3 scripts/announce_discord.py --no-ai         # rohe Commits ohne KI-Umformulierung
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# --- Pfade -----------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / "infra" / ".env"
STATE_PATH = REPO_ROOT / "scripts" / ".announce_state"  # letzter angekuendigter SHA

# Commit-Typen, die Spieler interessieren (Rest = chore/docs/test/refactor/ci -> ignoriert)
RELEVANT_PREFIXES = ("feat", "fix", "balance", "asset", "perf")
RELEVANT_RE = re.compile(r"^(" + "|".join(RELEVANT_PREFIXES) + r")(\([^)]*\))?!?:\s*(.+)$")

# Embed-Limits laut Discord
DISCORD_DESC_LIMIT = 4096
DISCORD_TOTAL_LIMIT = 6000

# Discord sitzt hinter Cloudflare und blockt den Default-User-Agent von urllib
# (Python-urllib/...) mit HTTP 403. Daher einen echten UA mitschicken.
USER_AGENT = "UniversePatchnotes/1.0 (+https://universe.tech-artist.de)"


# --- .env lesen ------------------------------------------------------------
def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


# --- Git -------------------------------------------------------------------
def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def read_state() -> str | None:
    if STATE_PATH.exists():
        sha = STATE_PATH.read_text(encoding="utf-8").strip()
        # Existiert der SHA noch (z. B. nach rebase)? Sonst ignorieren.
        try:
            git("cat-file", "-e", sha + "^{commit}")
            return sha
        except subprocess.CalledProcessError:
            return None
    return None


def write_state(sha: str) -> None:
    STATE_PATH.write_text(sha + "\n", encoding="utf-8")


def collect_commits(since: str | None) -> tuple[list[str], str]:
    """Gibt (relevante_betreffzeilen, head_sha) im Bereich since..HEAD zurueck."""
    head = git("rev-parse", "HEAD")
    if since:
        rng = f"{since}..HEAD"
    else:
        rng = "HEAD~10..HEAD"  # Fallback bei fehlendem State -> letzte 10
    raw = git("log", rng, "--pretty=format:%s", "--no-merges")
    subjects = [s for s in raw.splitlines() if s.strip()]
    relevant = []
    for s in subjects:
        m = RELEVANT_RE.match(s)
        if m:
            relevant.append(m.group(3).strip())  # nur die Beschreibung, ohne "feat(x):"
    return relevant, head


# --- Ollama ----------------------------------------------------------------
def ollama_patchnotes(env: dict[str, str], commits: list[str], model: str | None) -> str | None:
    """Commits -> spielerfreundliche deutsche Patch-Notes. None bei Ausfall."""
    base = env.get("OLLAMA_URL", "http://localhost:11434")
    # .env zeigt fuer Container auf host.docker.internal -> vom Host aus localhost.
    base = base.replace("host.docker.internal", "localhost").rstrip("/")
    model = model or "qwen3.5:9b"

    system = (
        "Du bist die Stimme von 'Universe', einem Weltraum-Aufbau-MMO. "
        "Du schreibst kurze, begeisternde deutsche Patch-Notes fuer Spieler. "
        "Aus technischen Commit-Zeilen machst du verstaendliche, knackige Punkte. "
        "Keine Fachbegriffe wie 'Backend', 'Endpoint', 'Refactor'. "
        "Gruppiere sinnvoll unter den Ueberschriften **Neu**, **Verbessert**, **Behoben** "
        "(nur Ueberschriften nutzen, zu denen es Punkte gibt). "
        "Jeder Punkt eine Zeile mit '- '. Maximal 12 Punkte. Kein Vorwort, kein Abschluss. "
        "WICHTIG: Erfinde KEINE Details, Zahlen oder Belohnungen, die nicht in der Zeile stehen. "
        "Technische Codes (z. B. 'HTTP 500', 'Fehler 500') sind KEINE Spielwerte und KEINE Waehrung "
        "-- schreib bei Fehlerbehebungen einfach 'Fehler behoben', ohne die Zahl zu deuten."
    )
    prompt = "Hier die Aenderungen seit dem letzten Update:\n" + "\n".join(f"- {c}" for c in commits)

    payload = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "think": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/generate",
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print(f"  ! Ollama nicht nutzbar ({exc}) -> Fallback auf rohe Commits", file=sys.stderr)
        return None
    text = (body or {}).get("response", "")
    text = text.strip() if isinstance(text, str) else ""
    return text or None


# --- Discord ---------------------------------------------------------------
def post_discord(webhook: str, title: str, description: str) -> None:
    if len(description) > DISCORD_DESC_LIMIT:
        description = description[: DISCORD_DESC_LIMIT - 20].rstrip() + "\n… (gekuerzt)"
    payload = {
        "username": "Universe Patchnotes",
        "embeds": [{
            "title": title,
            "description": description,
            "color": 0x5865F2,  # Discord-Blau
            "footer": {"text": "universe.tech-artist.de"},
        }],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError(f"Discord antwortete mit HTTP {resp.status}")


# --- Hauptlogik ------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Spiel-Updates als Discord-Patchnotes posten.")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts posten / State unveraendert")
    ap.add_argument("--since", help="Git-Ref/Tag/SHA als Startpunkt (statt letzter Ankuendigung)")
    ap.add_argument("--message", help="Freitext-Ankuendigung (ueberspringt Git und KI)")
    ap.add_argument("--no-ai", action="store_true", help="rohe Commits posten, ohne KI-Umformulierung")
    ap.add_argument("--model", help="Ollama-Modell (Standard: qwen3.5:9b)")
    ap.add_argument("--title", help="Embed-Titel ueberschreiben")
    args = ap.parse_args()

    env = load_env(ENV_PATH)
    webhook = env.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook and not args.dry_run:
        print("FEHLER: DISCORD_WEBHOOK_URL fehlt in infra/.env", file=sys.stderr)
        return 2

    today = datetime.now().strftime("%d.%m.%Y")
    title = args.title or f"🚀 Universe — Update vom {today}"
    head = None

    # --- Modus A: Freitext -------------------------------------------------
    if args.message:
        description = args.message
    # --- Modus B: aus Git --------------------------------------------------
    else:
        since = args.since or read_state()
        commits, head = collect_commits(since)
        if not commits:
            print("Keine spielrelevanten Aenderungen seit der letzten Ankuendigung. Nichts zu posten.")
            return 0
        print(f"  {len(commits)} relevante Aenderung(en) gefunden"
              + (f" (seit {since[:8]})" if since else " (Fallback: letzte 10 Commits)"))

        notes = None
        if not args.no_ai:
            notes = ollama_patchnotes(env, commits, args.model)
        description = notes if notes else "\n".join(f"- {c}" for c in commits)

    # --- Ausgabe / Posten --------------------------------------------------
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(description)
    print("=" * 60 + "\n")

    if args.dry_run:
        print("[dry-run] Nichts gepostet, State unveraendert.")
        return 0

    try:
        post_discord(webhook, title, description)
    except (urllib.error.URLError, OSError, RuntimeError) as exc:
        print(f"FEHLER beim Posten an Discord: {exc}", file=sys.stderr)
        return 1

    print("✓ An Discord gepostet.")
    # State nur bei Git-Modus fortschreiben (Freitext markiert keinen Commit-Stand)
    if head and not args.since:
        write_state(head)
        print(f"  State aktualisiert -> {head[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
