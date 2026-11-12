"""Unit tests for slot resolution, deduplication, formatting, and Telegram safety."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
import requests

from src.formatter import format_post_html, split_telegram_message
from src.generator import MissingApiKeyError, generate_unique_post
from src.history_store import (
    already_posted_slot,
    empty_history,
    load_history,
    normalize_homonym_pair,
    record_posted_items,
    save_history,
)
from src.schemas import (
    AfternoonPost,
    EveningPost,
    HomonymItem,
    IdiomItem,
    MorningPost,
    OwsItem,
    SpellingItem,
    SynAntItem,
    VocabItem,
)
from src.main import parse_args, run
from src.slots import IST, resolve_catchup_slot, resolve_slot
from src.telegram_client import send_telegram_html


def _sample_morning(offset: int = 0) -> MorningPost:
    return MorningPost(
        vocab=[
            VocabItem(
                word=f"Word{i + offset}",
                part_of_speech="adj.",
                meaning=f"Meaning <test & more> {i + offset}",
                example=f"Example sentence {i + offset}.",
            )
            for i in range(5)
        ],
        ows=[
            OwsItem(
                phrase=f"One who studies topic {i + offset}",
                word=f"Ows{i + offset}",
                example=f"He is an Ows{i + offset}.",
            )
            for i in range(5)
        ],
    )


def _sample_afternoon() -> AfternoonPost:
    return AfternoonPost(
        idioms=[
            IdiomItem(
                idiom=f"Idiom {i}",
                meaning=f"Idiom meaning {i}",
                example=f"He used idiom {i}.",
            )
            for i in range(5)
        ],
        syn_ant=[
            SynAntItem(
                word=f"Target{i}",
                meaning=f"Meaning {i}",
                synonyms=["Alpha", "Beta"],
                antonyms=["Gamma", "Delta"],
            )
            for i in range(5)
        ],
    )


def _sample_evening() -> EveningPost:
    return EveningPost(
        homonyms=[
            HomonymItem(
                word_1=f"PairA{i}",
                meaning_1="First meaning",
                word_2=f"PairB{i}",
                meaning_2="Second meaning",
                example_pair="Contrast example.",
            )
            for i in range(5)
        ],
        spelling=[
            SpellingItem(
                correct_word=f"Accommodation{i}",
                common_wrong_forms=[f"Accomodation{i}"],
                meaning="Lodging place",
                memory_tip="Double c, double m",
            )
            for i in range(5)
        ],
    )


class BotTests(unittest.TestCase):
    def test_slot_resolution_by_ist_time(self) -> None:
        self.assertEqual(resolve_slot("auto", datetime(2026, 11, 10, 7, 0, tzinfo=IST)).name, "morning")
        self.assertEqual(resolve_slot("auto", datetime(2026, 11, 10, 13, 0, tzinfo=IST)).name, "afternoon")
        self.assertEqual(resolve_slot("auto", datetime(2026, 11, 10, 19, 0, tzinfo=IST)).name, "evening")
        self.assertEqual(resolve_slot("evening", datetime(2026, 11, 10, 7, 0, tzinfo=IST)).name, "evening")

    def test_homonym_symmetry_normalization(self) -> None:
        self.assertEqual(
            normalize_homonym_pair("Affect", "Effect"),
            normalize_homonym_pair("effect", "AFFECT"),
        )

    def test_history_roundtrip_and_slot_guard(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            hist = empty_history()
            post = _sample_morning()
            record_posted_items(hist, ("vocab", "ows"), post, "2026-11-10", "morning")
            save_history(path, hist)

            loaded = load_history(path)
            self.assertTrue(already_posted_slot(loaded, "2026-11-10", "morning"))
            self.assertFalse(already_posted_slot(loaded, "2026-11-10", "afternoon"))
            self.assertEqual(len(loaded["vocab"]), 5)
            self.assertEqual(len(loaded["ows"]), 5)

    def test_generator_retries_on_duplicate_item(self) -> None:
        hist = empty_history()
        hist["vocab"].append("word0")
        calls = {"count": 0}

        def fake_invoker(spec, prompt, model):
            calls["count"] += 1
            if calls["count"] == 1:
                return _sample_morning(offset=0)
            return _sample_morning(offset=10)

        spec = resolve_slot("morning")
        result = generate_unique_post(spec, hist, retry_delay=0.0, invoker=fake_invoker)
        self.assertEqual(calls["count"], 2)
        self.assertEqual(result.vocab[0].word, "Word10")

    def test_generator_falls_back_across_models_on_503(self) -> None:
        hist = empty_history()
        tried_models = []

        def flaky_invoker(spec, prompt, model):
            tried_models.append(model)
            if model == "gemini-3.8-flash":
                raise RuntimeError("503 service_unavailable: high demand")
            return _sample_evening()

        result = generate_unique_post(
            resolve_slot("evening"), hist, retry_delay=0.0, invoker=flaky_invoker
        )
        self.assertEqual(tried_models, ["gemini-3.8-flash", "gemini-3.5-flash-lite"])
        self.assertEqual(len(result.homonyms), 5)

    def test_generator_fails_fast_on_missing_or_invalid_api_key(self) -> None:
        calls = {"count": 0}

        def missing_key_invoker(spec, prompt, model):
            calls["count"] += 1
            raise MissingApiKeyError("Missing key")

        with self.assertRaises(MissingApiKeyError):
            generate_unique_post(
                resolve_slot("evening"), empty_history(), retry_delay=0.0, invoker=missing_key_invoker
            )
        self.assertEqual(calls["count"], 1)

        invalid_calls = {"count": 0}

        def invalid_key_invoker(spec, prompt, model):
            invalid_calls["count"] += 1
            raise RuntimeError("400 API_KEY_INVALID")

        with self.assertRaises(RuntimeError):
            generate_unique_post(
                resolve_slot("evening"), empty_history(), retry_delay=0.0, invoker=invalid_key_invoker
            )
        self.assertEqual(invalid_calls["count"], 1)

    def test_format_html_escapes_special_chars_and_fits_slots(self) -> None:
        morning_html = format_post_html(resolve_slot("morning"), _sample_morning(), "10 Nov 2026")
        self.assertIn("&lt;test &amp; more&gt;", morning_html)
        self.assertIn("@sscstudyprephub", morning_html)

        afternoon_html = format_post_html(resolve_slot("afternoon"), _sample_afternoon(), "10 Nov 2026")
        self.assertIn("Idioms &amp; Phrases", afternoon_html)

        evening_html = format_post_html(resolve_slot("evening"), _sample_evening(), "10 Nov 2026")
        self.assertIn("Homonyms &amp; Homophones", evening_html)
        self.assertIn("Spelling Boosters", evening_html)

    def test_split_telegram_message_respects_limit(self) -> None:
        long_text = "\n".join([f"Line {i} " + ("x" * 60) for i in range(100)])
        chunks = split_telegram_message(long_text, max_length=1000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 1000 for c in chunks))

    @patch("src.telegram_client.requests.post")
    def test_telegram_error_masks_bot_token(self, mock_post: MagicMock) -> None:
        secret_token = "999999:SUPER_SECRET_BOT_TOKEN"
        mock_post.side_effect = requests.ConnectionError(
            f"HTTPSConnectionPool: url=https://api.telegram.org/bot{secret_token}/sendMessage"
        )
        with self.assertRaises(RuntimeError) as ctx:
            send_telegram_html("Hello", bot_token=secret_token, chat_id="@sscstudyprephub", max_retries=1)
        self.assertNotIn(secret_token, str(ctx.exception))
        self.assertIn("<REDACTED_TOKEN>", str(ctx.exception))

    @patch("src.main.send_telegram_html")
    @patch("src.main.generate_unique_post")
    @patch("src.main.current_ist_now")
    def test_main_dry_run_and_duplicate_skip(
        self,
        mock_now: MagicMock,
        mock_gen: MagicMock,
        mock_send: MagicMock,
    ) -> None:
        mock_now.return_value = datetime(2026, 11, 10, 7, 0, tzinfo=IST)
        mock_gen.return_value = _sample_morning()
        mock_send.return_value = [{"ok": True}]

        with TemporaryDirectory() as tmp:
            hist_path = Path(tmp) / "history.json"
            # Dry run should not call Telegram or save history.
            code = run(parse_args(["--slot", "morning", "--dry-run", "--history-file", str(hist_path)]))
            self.assertEqual(code, 0)
            mock_send.assert_not_called()
            self.assertFalse(hist_path.exists())

            # Real run sends once and persists history.
            code = run(parse_args(["--slot", "morning", "--history-file", str(hist_path)]))
            self.assertEqual(code, 0)
            self.assertEqual(mock_send.call_count, 1)
            self.assertTrue(already_posted_slot(load_history(hist_path), "2026-11-10", "morning"))

            # Re-running same slot without --force skips Telegram call.
            code = run(parse_args(["--slot", "morning", "--history-file", str(hist_path)]))
            self.assertEqual(code, 0)
            self.assertEqual(mock_send.call_count, 1)

    def test_catchup_slot_resolution(self) -> None:
        # Before morning window or between windows -> None
        self.assertIsNone(resolve_catchup_slot([], datetime(2026, 11, 12, 6, 30, tzinfo=IST)))
        self.assertIsNone(resolve_catchup_slot([], datetime(2026, 11, 12, 12, 35, tzinfo=IST)))
        # Inside afternoon window when unposted -> afternoon
        spec = resolve_catchup_slot(["2026-11-12:morning"], datetime(2026, 11, 12, 14, 17, tzinfo=IST))
        self.assertIsNotNone(spec)
        self.assertEqual(spec.name, "afternoon")
        # Already posted -> None
        self.assertIsNone(
            resolve_catchup_slot(
                ["2026-11-12:morning", "2026-11-12:afternoon"],
                datetime(2026, 11, 12, 14, 17, tzinfo=IST),
            )
        )

    @patch("src.main.send_telegram_html")
    @patch("src.main.generate_unique_post")
    @patch("src.main.current_ist_now")
    def test_main_catchup_posts_once_and_skips_after(
        self,
        mock_now: MagicMock,
        mock_gen: MagicMock,
        mock_send: MagicMock,
    ) -> None:
        mock_now.return_value = datetime(2026, 11, 12, 19, 17, tzinfo=IST)
        mock_gen.return_value = _sample_evening()
        mock_send.return_value = [{"ok": True}]

        with TemporaryDirectory() as tmp:
            hist_path = Path(tmp) / "history.json"
            self.assertEqual(run(parse_args(["--slot", "catchup", "--history-file", str(hist_path)])), 0)
            self.assertEqual(mock_send.call_count, 1)
            self.assertTrue(already_posted_slot(load_history(hist_path), "2026-11-12", "evening"))

            # Second catchup run in same evening window skips cleanly.
            self.assertEqual(run(parse_args(["--slot", "catchup", "--history-file", str(hist_path)])), 0)
            self.assertEqual(mock_send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
