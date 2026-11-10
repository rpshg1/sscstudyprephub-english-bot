"""Telegram Bot API sender with safe error handling and rate-limit retries."""

import os
import time
from typing import List
import requests

from .formatter import split_telegram_message

TELEGRAM_API_BASE = "https://api.telegram.org"


def _mask_token(message: str, token: str) -> str:
    """Ensure the bot token never appears in exception messages or logs."""
    return message.replace(token, "<REDACTED_TOKEN>") if token else message


def send_telegram_html(
    text: str,
    bot_token: str | None = None,
    chat_id: str | None = None,
    max_retries: int = 3,
) -> List[dict]:
    """Post an HTML-formatted message (splitting if >4000 chars) to Telegram."""
    token = (bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
    target_chat = (chat_id or os.getenv("TELEGRAM_CHAT_ID", "")).strip() or "@sscstudyprephub"

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing. Set it in .env locally or as a GitHub Actions Secret."
        )

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    chunks = split_telegram_message(text)
    responses: List[dict] = []

    for index, chunk in enumerate(chunks, start=1):
        payload = {
            "chat_id": target_chat,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=30)
                data = resp.json()
            except requests.RequestException as exc:
                safe_err = _mask_token(str(exc), token)
                if attempt == max_retries:
                    raise RuntimeError(f"Telegram network error on part {index}: {safe_err}") from None
                time.sleep(2 * attempt)
                continue
            except ValueError:
                if attempt == max_retries:
                    raise RuntimeError(f"Telegram returned non-JSON response (HTTP {resp.status_code}).")
                time.sleep(2 * attempt)
                continue

            if data.get("ok"):
                responses.append(data)
                break

            error_code = data.get("error_code")
            retry_after = data.get("parameters", {}).get("retry_after")
            if error_code == 429 and retry_after and attempt < max_retries:
                time.sleep(int(retry_after) + 1)
                continue

            desc = _mask_token(str(data.get("description", "Unknown Telegram error")), token)
            raise RuntimeError(f"Telegram API error ({error_code}): {desc}")

    return responses
