from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from update_profile import (  # noqa: E402
    REPOSITORIES_END,
    REPOSITORIES_START,
    parse_github_repository,
    render_repositories,
    replace_section,
)


class ProfileUpdaterTests(unittest.TestCase):
    def test_parses_and_renders_repository_signals(self) -> None:
        repositories = [
            parse_github_repository(
                (
                    "{"
                    f'"full_name":"{full_name}",'
                    f'"html_url":"https://github.com/{full_name}",'
                    f'"stargazers_count":{index * 1000},'
                    f'"forks_count":{index}'
                    "}"
                ).encode()
            )
            for index, full_name in enumerate(
                (
                    "yhay81/pylopdf",
                    "yhay81/GASlacker",
                    "yhay81/public-data-catalog",
                ),
                start=1,
            )
        ]

        rendered = render_repositories(repositories)

        self.assertIn("**[pylopdf](https://github.com/yhay81/pylopdf)**", rendered)
        self.assertIn("`★ 1,000` `forks 1`", rendered)
        self.assertIn("`★ 2,000` `forks 2`", rendered)
        self.assertLess(rendered.index("pylopdf"), rendered.index("GASlacker"))

    def test_replaces_exactly_one_marker_pair(self) -> None:
        document = f"before\n{REPOSITORIES_START}\nold\n{REPOSITORIES_END}\nafter\n"

        updated = replace_section(
            document,
            REPOSITORIES_START,
            REPOSITORIES_END,
            "new",
        )

        self.assertEqual(
            updated,
            f"before\n{REPOSITORIES_START}\nnew\n{REPOSITORIES_END}\nafter\n",
        )

    def test_rejects_missing_markers(self) -> None:
        with self.assertRaises(ValueError):
            replace_section(
                "no markers",
                REPOSITORIES_START,
                REPOSITORIES_END,
                "new",
            )


if __name__ == "__main__":
    unittest.main()
