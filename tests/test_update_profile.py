from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from update_profile import (  # noqa: E402
    TELEMETRY_END,
    TELEMETRY_START,
    WRITING_END,
    WRITING_START,
    parse_zenn_feed,
    render_telemetry,
    render_writing,
    replace_section,
)


class ProfileUpdaterTests(unittest.TestCase):
    def test_parses_and_sorts_rss_posts(self) -> None:
        feed = b"""\
<rss><channel>
  <item>
    <title>Older post</title>
    <link>https://example.com/older</link>
    <pubDate>Wed, 31 Dec 2025 05:06:33 GMT</pubDate>
  </item>
  <item>
    <title>Newest [post]</title>
    <link>https://example.com/newest</link>
    <pubDate>Wed, 22 Jul 2026 16:01:49 GMT</pubDate>
  </item>
</channel></rss>
"""
        posts = parse_zenn_feed(feed)

        self.assertEqual([post.title for post in posts], ["Newest [post]", "Older post"])
        self.assertIn(r"Newest \[post\]", render_writing(posts))

    def test_replaces_exactly_one_marker_pair(self) -> None:
        document = f"before\n{WRITING_START}\nold\n{WRITING_END}\nafter\n"

        updated = replace_section(document, WRITING_START, WRITING_END, "new")

        self.assertEqual(
            updated,
            f"before\n{WRITING_START}\nnew\n{WRITING_END}\nafter\n",
        )

    def test_rejects_missing_markers(self) -> None:
        with self.assertRaises(ValueError):
            replace_section("no markers", WRITING_START, WRITING_END, "new")

    def test_hides_inactive_telemetry(self) -> None:
        self.assertEqual(render_telemetry({"data": {"total_seconds": 299}}), "")

    def test_renders_compact_active_telemetry(self) -> None:
        payload = {
            "data": {
                "total_seconds": 7200,
                "human_readable_total_including_other_language": "2 hrs",
                "languages": [
                    {"name": "Python", "percent": 62.4},
                    {"name": "Rust", "percent": 34.6},
                    {"name": "Other", "percent": 0.5},
                ],
            }
        }

        telemetry = render_telemetry(payload)

        self.assertIn("<details>", telemetry)
        self.assertIn("last 7 days · 2 hrs", telemetry)
        self.assertIn("`Python` 62% · `Rust` 35%", telemetry)
        self.assertNotIn("Other", telemetry)

    def test_empty_section_keeps_markers_adjacent(self) -> None:
        document = f"{TELEMETRY_START}\nold\n{TELEMETRY_END}"

        updated = replace_section(document, TELEMETRY_START, TELEMETRY_END, "")

        self.assertEqual(updated, f"{TELEMETRY_START}\n{TELEMETRY_END}")


if __name__ == "__main__":
    unittest.main()
