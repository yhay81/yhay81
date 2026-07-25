"""Refresh first-party repository signals in the GitHub profile README.

RSS rendering is intentionally delegated to blog-post-workflow. This script
keeps the custom part small: it reads public GitHub repository metadata and
leaves existing content untouched when the API is unavailable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

GITHUB_REPOSITORY_URL = "https://api.github.com/repos/{repository}"
USER_AGENT = "yhay81-profile-updater/2.0"

REPOSITORIES_START = "<!-- profile:repositories:start -->"
REPOSITORIES_END = "<!-- profile:repositories:end -->"

REPOSITORIES = (
    (
        "yhay81/pylopdf",
        "Python ergonomics over a Rust PDF core; small wheels and zero runtime dependencies.",
        "Python / Rust",
    ),
    (
        "yhay81/GASlacker",
        "A production-minded Slack Web API client: 168 methods, rate-limit retries, uploads, and OAuth v2.",
        "TypeScript / GAS",
    ),
    (
        "yhay81/public-data-catalog",
        "AI-friendly public API and dataset metadata, published in machine-readable form.",
        "Python / Data",
    ),
)


@dataclass(frozen=True)
class RepositorySignal:
    full_name: str
    url: str
    stars: int
    forks: int


def fetch_bytes(url: str, *, authorization: str | None = None) -> bytes:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if authorization:
        headers["Authorization"] = authorization
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def parse_github_repository(payload: bytes) -> RepositorySignal:
    data = json.loads(payload)
    return RepositorySignal(
        full_name=str(data["full_name"]),
        url=str(data["html_url"]),
        stars=int(data.get("stargazers_count") or 0),
        forks=int(data.get("forks_count") or 0),
    )


def render_repositories(repositories: list[RepositorySignal]) -> str:
    by_name = {repository.full_name: repository for repository in repositories}
    lines = [
        "| Project | Engineering signal | Live OSS telemetry |",
        "|:--|:--|:--|",
    ]

    for full_name, engineering_signal, stack in REPOSITORIES:
        repository = by_name[full_name]
        project_name = full_name.split("/", 1)[1]
        lines.append(
            f"| **[{project_name}]({repository.url})** "
            f"| {engineering_signal} "
            f"| `★ {repository.stars:,}` `forks {repository.forks:,}` · {stack} |"
        )

    return "\n".join(lines)


def replace_section(document: str, start: str, end: str, content: str) -> str:
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f"Expected one marker pair: {start} … {end}")

    before, remainder = document.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n{content}\n{end}{after}"


def refresh(
    document: str,
    *,
    github_token: str | None = None,
) -> tuple[str, list[str]]:
    updated = document
    messages: list[str] = []

    try:
        authorization = f"Bearer {github_token}" if github_token else None
        repositories = [
            parse_github_repository(
                fetch_bytes(
                    GITHUB_REPOSITORY_URL.format(repository=repository),
                    authorization=authorization,
                )
            )
            for repository, _, _ in REPOSITORIES
        ]
        updated = replace_section(
            updated,
            REPOSITORIES_START,
            REPOSITORIES_END,
            render_repositories(repositories),
        )
        messages.append(f"GitHub: refreshed {len(repositories)} repository signals")
    except (
        json.JSONDecodeError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        urllib.error.URLError,
    ) as error:
        messages.append(f"GitHub: kept existing content ({error})")

    return updated, messages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--readme",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "README.md",
        help="README file to update",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report whether the README would change without writing it",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    document = args.readme.read_text(encoding="utf-8")
    updated, messages = refresh(
        document,
        github_token=os.environ.get("GITHUB_TOKEN"),
    )

    for message in messages:
        print(message, file=sys.stderr)

    if updated == document:
        print("README is already current.")
        return 0
    if args.check:
        print("README would change.")
        return 1

    args.readme.write_text(updated, encoding="utf-8", newline="\n")
    print("README updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
