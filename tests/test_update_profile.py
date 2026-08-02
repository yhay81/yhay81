from __future__ import annotations

import sys
import unittest
import urllib.error
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from update_profile import (
    FOOTPRINT_BAR_WIDTH,
    GITHUB_API_VERSION,
    WRITING_END,
    WRITING_MINIMUM_ENTRIES,
    WRITING_RECENT_WINDOW_DAYS,
    WRITING_START,
    GitHubProfile,
    LanguageCategory,
    PublicRepository,
    WritingEntry,
    allocate_widths,
    build_outputs,
    fetch_json,
    language_categories,
    parse_zenn_feed,
    replace_section,
    select_writing,
)


def writing_entries(*published_on: str) -> tuple[WritingEntry, ...]:
    return tuple(
        WritingEntry(
            title=f"Article {index}",
            url=f"https://zenn.dev/yhay81/articles/{index}",
            published_on=day,
        )
        for index, day in enumerate(published_on, start=1)
    )


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class ProfileUpdaterTests(unittest.TestCase):
    def test_replaces_exactly_one_marker_pair(self) -> None:
        document = f"before\n{WRITING_START}\nold\n{WRITING_END}\nafter\n"

        updated = replace_section(
            document,
            WRITING_START,
            WRITING_END,
            "new",
        )

        self.assertEqual(
            updated,
            f"before\n{WRITING_START}\nnew\n{WRITING_END}\nafter\n",
        )

    def test_rejects_missing_markers(self) -> None:
        with self.assertRaises(ValueError):
            replace_section(
                "no markers",
                WRITING_START,
                WRITING_END,
                "new",
            )

    def test_allocates_every_bar_pixel_deterministically(self) -> None:
        widths = allocate_widths([13, 6, 3, 2], FOOTPRINT_BAR_WIDTH)

        self.assertEqual(widths, [290, 134, 67, 45])
        self.assertEqual(sum(widths), FOOTPRINT_BAR_WIDTH)
        self.assertEqual(allocate_widths([0, 0], 100), [0, 0])

    def test_builds_readme_and_footprint_from_one_snapshot(self) -> None:
        repositories = tuple(
            PublicRepository(
                full_name=f"yhay81/example-{index}",
                url=f"https://github.com/yhay81/example-{index}",
                stars=index,
                forks=index - 1,
                language=language,
                is_fork=False,
            )
            for index, language in enumerate(
                ("Rust", "JavaScript", "Python", "Python", "Python", "JavaScript"),
                start=1,
            )
        )
        profile = GitHubProfile(
            public_repositories=51,
            followers=63,
            repositories=repositories,
        )
        document = f"Proof stays static.\n{WRITING_START}\nold\n{WRITING_END}\n"
        template = (
            "$public_repositories|$stars|$forks|$followers|$leading_language|$language_counts"
        )
        writing = (
            WritingEntry(
                title="A [reliable] profile",
                url="https://zenn.dev/yhay81/articles/reliable-profile",
                published_on="2026-07-25",
            ),
        )

        updated_document, footprint = build_outputs(
            document,
            template,
            profile,
            writing,
        )

        self.assertIn("Proof stays static.", updated_document)
        self.assertIn(
            r"- [A \[reliable\] profile](https://zenn.dev/yhay81/articles/reliable-profile)",
            updated_document,
        )
        self.assertEqual(
            footprint,
            "51|21|15|63|Python|3 · 2 · 1 · 0 · 0",
        )
        self.assertEqual(
            language_categories(profile),
            (
                LanguageCategory("Python", 3),
                LanguageCategory("JavaScript", 2),
                LanguageCategory("Rust", 1),
                LanguageCategory("—", 0),
                LanguageCategory("Other", 0),
            ),
        )

    def test_parses_zenn_feed_in_utc_order(self) -> None:
        payload = b"""\
<rss><channel>
  <item>
    <title>First article</title>
    <link>https://zenn.dev/yhay81/articles/first</link>
    <pubDate>Sat, 25 Jul 2026 23:30:00 +0900</pubDate>
  </item>
  <item>
    <title>Second article</title>
    <link>https://zenn.dev/yhay81/articles/second</link>
    <pubDate>Fri, 24 Jul 2026 09:17:41 GMT</pubDate>
  </item>
  <item>
    <title>Engineering book</title>
    <link>https://zenn.dev/yhay81/books/engineering</link>
    <pubDate>Thu, 23 Jul 2026 10:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""

        entries = parse_zenn_feed(payload)

        self.assertEqual(
            entries,
            (
                WritingEntry(
                    title="First article",
                    url="https://zenn.dev/yhay81/articles/first",
                    published_on="2026-07-25",
                ),
                WritingEntry(
                    title="Second article",
                    url="https://zenn.dev/yhay81/articles/second",
                    published_on="2026-07-24",
                ),
                WritingEntry(
                    title="Engineering book",
                    url="https://zenn.dev/yhay81/books/engineering",
                    published_on="2026-07-23",
                ),
            ),
        )

    def test_keeps_the_newest_minimum_when_the_recent_window_is_quiet(self) -> None:
        entries = writing_entries(
            "2026-06-30",
            "2026-08-01",
            "2026-05-01",
            "2026-07-20",
            "2026-03-01",
            "2026-06-01",
            "2026-04-01",
        )

        selected = select_writing(entries, today=date(2026, 8, 3))

        self.assertEqual(len(selected), WRITING_MINIMUM_ENTRIES)
        self.assertEqual(
            [entry.published_on for entry in selected],
            ["2026-08-01", "2026-07-20", "2026-06-30", "2026-06-01", "2026-05-01"],
        )

    def test_keeps_every_entry_inside_a_busy_recent_window(self) -> None:
        entries = writing_entries(
            "2026-08-02",
            "2026-08-01",
            "2026-07-28",
            "2026-07-25",
            "2026-07-20",
            "2026-07-10",
            "2026-07-04",  # exactly WRITING_RECENT_WINDOW_DAYS old, so still inside
            "2026-07-03",
            "2026-06-01",
        )

        selected = select_writing(entries, today=date(2026, 8, 3))

        self.assertEqual(WRITING_RECENT_WINDOW_DAYS, 30)
        self.assertEqual(
            [entry.published_on for entry in selected],
            [
                "2026-08-02",
                "2026-08-01",
                "2026-07-28",
                "2026-07-25",
                "2026-07-20",
                "2026-07-10",
                "2026-07-04",
            ],
        )

    def test_rejects_a_feed_shorter_than_the_minimum(self) -> None:
        entries = writing_entries("2026-08-01", "2026-07-20", "2026-06-30")

        with self.assertRaises(ValueError):
            select_writing(entries, today=date(2026, 8, 3))

    def test_fetch_json_uses_versioned_api_and_retries_transient_failures(self) -> None:
        requests: list[urllib.request.Request] = []
        sleeps: list[float] = []
        responses: list[object] = [
            urllib.error.HTTPError(
                "https://api.github.com/example",
                503,
                "unavailable",
                {"Retry-After": "0"},
                None,
            ),
            FakeResponse(b'{"ok": true}'),
        ]

        def urlopen(request: urllib.request.Request, *, timeout: int) -> object:
            self.assertEqual(timeout, 20)
            requests.append(request)
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        payload = fetch_json(
            "https://api.github.com/example",
            authorization="Bearer test-token",
            attempts=2,
            urlopen=urlopen,
            sleep=sleeps.append,
        )

        headers = {name.casefold(): value for name, value in requests[-1].header_items()}
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(headers["x-github-api-version"], GITHUB_API_VERSION)
        self.assertEqual(headers["authorization"], "Bearer test-token")
        self.assertEqual(sleeps, [0.0])


if __name__ == "__main__":
    unittest.main()
