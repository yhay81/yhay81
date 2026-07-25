from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from update_profile import (
    FOOTPRINT_BAR_WIDTH,
    GITHUB_API_VERSION,
    REPOSITORIES_END,
    REPOSITORIES_START,
    GitHubProfile,
    PublicRepository,
    RepositorySignal,
    allocate_widths,
    build_outputs,
    fetch_json,
    render_repositories,
    replace_section,
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
    def test_renders_repository_signals(self) -> None:
        repositories = [
            RepositorySignal(
                full_name=full_name,
                url=f"https://github.com/{full_name}",
                stars=index * 1000,
                forks=index,
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

    def test_allocates_every_bar_pixel_deterministically(self) -> None:
        widths = allocate_widths([13, 6, 3, 2], FOOTPRINT_BAR_WIDTH)

        self.assertEqual(widths, [290, 134, 67, 45])
        self.assertEqual(sum(widths), FOOTPRINT_BAR_WIDTH)
        self.assertEqual(allocate_widths([0, 0], 100), [0, 0])

    def test_builds_readme_and_footprint_from_one_snapshot(self) -> None:
        repositories = tuple(
            PublicRepository(
                full_name=full_name,
                url=f"https://github.com/{full_name}",
                stars=index,
                forks=index - 1,
                language=language,
                is_fork=False,
            )
            for index, (full_name, language) in enumerate(
                (
                    ("yhay81/pylopdf", "Rust"),
                    ("yhay81/GASlacker", "JavaScript"),
                    ("yhay81/public-data-catalog", "Python"),
                ),
                start=1,
            )
        )
        profile = GitHubProfile(
            public_repositories=51,
            followers=63,
            repositories=repositories,
        )
        document = f"{REPOSITORIES_START}\nold\n{REPOSITORIES_END}\n"
        template = (
            "$generated_at|$public_repositories|$stars|$forks|$followers|"
            "$language_1_width|$language_2_x|$language_2_width|"
            "$language_3_x|$language_3_width|$language_4_x|"
            "$language_4_width|$language_counts"
        )

        updated_document, footprint = build_outputs(
            document,
            template,
            profile,
            generated_at="2026-07-25",
        )

        self.assertIn("**[pylopdf](https://github.com/yhay81/pylopdf)**", updated_document)
        self.assertEqual(
            footprint,
            "2026-07-25|51|6|3|63|179|179|179|358|178|536|0|1 · 1 · 1 · 0",
        )

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
