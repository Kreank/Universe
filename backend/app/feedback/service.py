"""Telegram-Benachrichtigung fuer eingehendes Spieler-Feedback.

Best-effort: Schlaegt der Push fehl (Bot nicht konfiguriert, Netzfehler, Telegram down),
darf das den Request NICHT scheitern lassen — das Feedback liegt bereits sicher in der DB.
Der Push ist nur die Sofort-Meldung aufs Handy des Entwicklers."""
from __future__ import annotations

import logging

import httpx

from app.platform.config import settings

log = logging.getLogger("universe.feedback")

_CATEGORY_LABEL = {"bug": "🐞 Bug", "idea": "💡 Idee", "other": "💬 Sonstiges"}


async def notify_telegram(
    *, category: str, message: str, display_name: str, page: str | None
) -> None:
    """Schickt eine Feedback-Meldung an den konfigurierten Telegram-Chat (best-effort)."""
    token = settings.FEEDBACK_TELEGRAM_BOT_TOKEN.strip()
    chat_id = settings.FEEDBACK_TELEGRAM_CHAT_ID.strip()
    if not token or not chat_id:
        # Nicht konfiguriert -> still ueberspringen (Feedback bleibt in der DB).
        return

    label = _CATEGORY_LABEL.get(category, category)
    text = (
        f"{label} · Universe-Feedback\n"
        f"👤 {display_name}\n"
        f"📍 {page or '—'}\n\n"
        f"{message}"
    )
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            )
            resp.raise_for_status()
    except Exception:  # noqa: BLE001 — Push darf den Request nie kippen
        log.warning("Feedback-Telegram-Push fehlgeschlagen (Feedback ist in der DB gesichert)")
