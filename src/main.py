"""CLI entrypoint for generating and posting SSC English doses to Telegram."""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from .formatter import format_post_html
from .generator import DEFAULT_MODEL, generate_unique_post
from .history_store import (
    already_posted_slot,
    load_history,
    record_posted_items,
    save_history,
)
from .slots import current_ist_now, is_within_slot_window, resolve_catchup_slot, resolve_slot
from .telegram_client import send_telegram_html

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "history.json"


def _configure_utf8_stdout() -> None:
    """Prevent UnicodeEncodeError on Windows consoles when printing emoji previews."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Post daily SSC English vocab/OWS/idioms/syn-ant/homonyms/spelling to Telegram."
    )
    parser.add_argument(
        "--slot",
        default=os.getenv("POST_SLOT", "auto"),
        choices=["auto", "catchup", "morning", "afternoon", "evening"],
        help="Target slot (defaults to POST_SLOT env var or IST time auto-detection).",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
        help=f"Gemini model name (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--history-file",
        type=Path,
        default=DEFAULT_HISTORY_PATH,
        help="Path to history JSON used to prevent repeated words.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and print the Telegram message without posting or updating history.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=os.getenv("FORCE_RUN", "").lower() in ("true", "1"),
        help="Post even if this slot was already posted today (IST) or outside slot window.",
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    """Execute one scheduled or manual posting run."""
    load_dotenv()
    _configure_utf8_stdout()

    now_ist = current_ist_now()
    date_iso = now_ist.strftime("%Y-%m-%d")
    date_label = now_ist.strftime("%d %b %Y")
    history = load_history(args.history_file)

    if args.slot == "catchup":
        spec = resolve_catchup_slot(history.get("posted_log", []), now_ist=now_ist)
        if spec is None:
            print(f"[Skip] No due unposted slot at {now_ist.strftime('%H:%M')} IST ({date_iso}).")
            return 0
    else:
        spec = resolve_slot(args.slot, now_ist=now_ist)
        if not args.dry_run and not args.force and already_posted_slot(history, date_iso, spec.name):
            print(f"[Skip] Slot '{spec.name}' already posted on {date_iso} IST. Pass --force to override.")
            return 0
        if not args.dry_run and not args.force and not is_within_slot_window(spec.name, now_ist=now_ist):
            print(
                f"\n==================================================\n"
                f"[BLOCKED] Current time is {now_ist.strftime('%I:%M %p')} IST.\n"
                f"[BLOCKED] Outside allowed posting window for '{spec.name}' dose ({spec.schedule_label}).\n"
                f"[BLOCKED] Cron was delayed by GitHub runner. Aborting cleanly to prevent student disturbance.\n"
                f"=================================================="
            )
            return 0

    print(f"Generating '{spec.name}' ({spec.schedule_label}) post for {date_label} using {args.model}...")
    post_data = generate_unique_post(spec=spec, history=history, model=args.model)
    message_html = format_post_html(spec=spec, post_data=post_data, date_label=date_label)

    if args.dry_run:
        print("\n--- DRY RUN PREVIEW (NOT SENT TO TELEGRAM) ---\n")
        print(message_html)
        print("\n--- END PREVIEW ---")
        return 0

    responses = send_telegram_html(message_html)
    record_posted_items(
        history=history,
        categories=spec.categories,
        post_data=post_data,
        date_ist=date_iso,
        slot=spec.name,
    )
    save_history(args.history_file, history)
    print(f"[Success] Posted '{spec.name}' dose to Telegram ({len(responses)} message(s)) and updated history.")
    return 0


def main() -> int:
    """CLI wrapper returning process exit code."""
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
