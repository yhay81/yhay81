"""Refresh public GitHub signals, the engineering footprint, and latest writing.

All remote data is fetched and rendered with the Python standard library so the
write-enabled workflow does not need to run third-party Actions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime
from pathlib import Path
from string import Template
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree
from xml.sax.saxutils import escape as escape_xml

GITHUB_API_VERSION = "2026-03-10"
GITHUB_PROFILE_URL = "https://api.github.com/users/yhay81"
GITHUB_REPOSITORIES_URL = (
    "https://api.github.com/users/yhay81/repos?type=owner&sort=updated&per_page=100&page={page}"
)
ZENN_FEED_URL = "https://zenn.dev/yhay81/feed"
USER_AGENT = "yhay81-profile-updater/4.0"
RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})

REPOSITORIES_START = "<!-- profile:repositories:start -->"
REPOSITORIES_END = "<!-- profile:repositories:end -->"
WRITING_START = "<!-- BLOG-POST-LIST:START -->"
WRITING_END = "<!-- BLOG-POST-LIST:END -->"
WRITING_ENTRY_LIMIT = 3

FEATURED_REPOSITORIES = (
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

FOOTPRINT_BAR_WIDTH = 536
FOOTPRINT_LANGUAGE_LIMIT = 4
FOOTPRINT_LANGUAGE_LABEL_X = (18, 126, 234, 342, 450)
FOOTPRINT_LANGUAGE_COLORS = ("cyan", "violet", "orange", "pink", "green")


@dataclass(frozen=True)
class RepositorySignal:
    full_name: str
    url: str
    stars: int
    forks: int


@dataclass(frozen=True)
class PublicRepository:
    full_name: str
    url: str
    stars: int
    forks: int
    language: str | None
    is_fork: bool


@dataclass(frozen=True)
class GitHubProfile:
    public_repositories: int
    followers: int
    repositories: tuple[PublicRepository, ...]


@dataclass(frozen=True)
class WritingEntry:
    title: str
    url: str
    published_on: str


@dataclass(frozen=True)
class LanguageCategory:
    name: str
    count: int


def fetch_bytes(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    attempts: int = 3,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    """Fetch a remote payload with bounded retries."""

    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    request = urllib.request.Request(url, headers=dict(headers or {}))

    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=20) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in RETRYABLE_HTTP_STATUSES or attempt == attempts - 1:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else float(2**attempt)
        except OSError:
            if attempt == attempts - 1:
                raise
            delay = float(2**attempt)

        sleep(max(0.0, min(delay, 5.0)))

    raise AssertionError("retry loop exited unexpectedly")


def fetch_json(
    url: str,
    *,
    authorization: str | None = None,
    attempts: int = 3,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> object:
    """Fetch and decode a versioned GitHub API response."""

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if authorization:
        headers["Authorization"] = authorization
    payload = fetch_bytes(
        url,
        headers=headers,
        attempts=attempts,
        urlopen=urlopen,
        sleep=sleep,
    )
    return json.loads(payload)


def parse_zenn_feed(
    payload: bytes, *, limit: int = WRITING_ENTRY_LIMIT
) -> tuple[WritingEntry, ...]:
    """Parse and validate the newest entries from the configured Zenn RSS feed."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    root = ElementTree.fromstring(payload)
    entries: list[WritingEntry] = []
    for item in root.findall("./channel/item"):
        title = " ".join((item.findtext("title") or "").split())
        url = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        if not title or not url or not published:
            raise ValueError("Zenn feed entries must include title, link, and pubDate")

        parsed_url = urlparse(url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "zenn.dev"
            or not parsed_url.path.startswith("/yhay81/")
        ):
            raise ValueError(f"Unexpected Zenn writing URL: {url}")

        published_at = parsedate_to_datetime(published)
        if published_at is None:
            raise ValueError(f"Invalid Zenn publication date: {published}")
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)

        entries.append(
            WritingEntry(
                title=title,
                url=url,
                published_on=published_at.astimezone(UTC).date().isoformat(),
            )
        )
        if len(entries) == limit:
            break

    if len(entries) != limit:
        raise ValueError(f"Expected at least {limit} Zenn feed entries")
    return tuple(entries)


def fetch_zenn_writing(
    *,
    limit: int = WRITING_ENTRY_LIMIT,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[WritingEntry, ...]:
    payload = fetch_bytes(
        ZENN_FEED_URL,
        headers={
            "Accept": "application/rss+xml, application/xml;q=0.9",
            "User-Agent": USER_AGENT,
        },
        urlopen=urlopen,
        sleep=sleep,
    )
    return parse_zenn_feed(payload, limit=limit)


def parse_public_repository(data: Mapping[str, object]) -> PublicRepository:
    language = data.get("language")
    return PublicRepository(
        full_name=str(data["full_name"]),
        url=str(data["html_url"]),
        stars=int(data.get("stargazers_count") or 0),
        forks=int(data.get("forks_count") or 0),
        language=str(language) if language else None,
        is_fork=bool(data.get("fork")),
    )


def fetch_github_profile(github_token: str | None = None) -> GitHubProfile:
    authorization = f"Bearer {github_token}" if github_token else None
    profile = fetch_json(GITHUB_PROFILE_URL, authorization=authorization)
    if not isinstance(profile, dict):
        raise TypeError("GitHub profile response must be an object")

    repositories: list[PublicRepository] = []
    for page in range(1, 11):
        payload = fetch_json(
            GITHUB_REPOSITORIES_URL.format(page=page),
            authorization=authorization,
        )
        if not isinstance(payload, list):
            raise TypeError("GitHub repositories response must be an array")
        for repository in payload:
            if not isinstance(repository, dict):
                raise TypeError("GitHub repository entries must be objects")
            repositories.append(parse_public_repository(repository))
        if len(payload) < 100:
            break
    else:
        raise ValueError("GitHub repository pagination exceeded the safety limit")

    return GitHubProfile(
        public_repositories=int(profile["public_repos"]),
        followers=int(profile["followers"]),
        repositories=tuple(repositories),
    )


def featured_repository_signals(profile: GitHubProfile) -> list[RepositorySignal]:
    by_name = {repository.full_name.casefold(): repository for repository in profile.repositories}
    signals: list[RepositorySignal] = []
    for full_name, _, _ in FEATURED_REPOSITORIES:
        repository = by_name[full_name.casefold()]
        signals.append(
            RepositorySignal(
                full_name=repository.full_name,
                url=repository.url,
                stars=repository.stars,
                forks=repository.forks,
            )
        )
    return signals


def render_repositories(repositories: list[RepositorySignal]) -> str:
    by_name = {repository.full_name.casefold(): repository for repository in repositories}
    lines = [
        "| Project | Engineering signal | Live OSS telemetry |",
        "|:--|:--|:--|",
    ]

    for full_name, engineering_signal, stack in FEATURED_REPOSITORIES:
        repository = by_name[full_name.casefold()]
        project_name = full_name.split("/", 1)[1]
        lines.append(
            f"| **[{project_name}]({repository.url})** "
            f"| {engineering_signal} "
            f"| `★ {repository.stars:,}` `forks {repository.forks:,}` · {stack} |"
        )

    return "\n".join(lines)


def escape_markdown_link_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def render_writing(entries: Sequence[WritingEntry]) -> str:
    return "\n".join(
        f"- [{escape_markdown_link_text(entry.title)}]({entry.url}) — {entry.published_on}"
        for entry in entries
    )


def allocate_widths(counts: Sequence[int], total: int) -> list[int]:
    """Allocate integer SVG widths without losing or inventing pixels."""

    if total < 0 or any(count < 0 for count in counts):
        raise ValueError("counts and total must be non-negative")
    count_total = sum(counts)
    if count_total == 0:
        return [0] * len(counts)

    exact = [count * total / count_total for count in counts]
    widths = [int(width) for width in exact]
    remainder = total - sum(widths)
    order = sorted(
        range(len(counts)),
        key=lambda index: (exact[index] - widths[index], -index),
        reverse=True,
    )
    for index in order[:remainder]:
        widths[index] += 1
    return widths


def language_categories(profile: GitHubProfile) -> tuple[LanguageCategory, ...]:
    original = [repository for repository in profile.repositories if not repository.is_fork]
    language_counts = Counter(
        repository.language for repository in original if repository.language is not None
    )
    ranked = sorted(
        language_counts.items(),
        key=lambda item: (-item[1], item[0].casefold(), item[0]),
    )
    leading = [
        LanguageCategory(name=language, count=count)
        for language, count in ranked[:FOOTPRINT_LANGUAGE_LIMIT]
    ]
    while len(leading) < FOOTPRINT_LANGUAGE_LIMIT:
        leading.append(LanguageCategory(name="—", count=0))

    other = sum(count for _, count in ranked[FOOTPRINT_LANGUAGE_LIMIT:])
    return (*leading, LanguageCategory(name="Other", count=other))


def render_language_legend(categories: Sequence[LanguageCategory]) -> str:
    return "\n    ".join(
        f'<text x="{x}" y="53" class="mono">{escape_xml(category.name)}</text>'
        for x, category in zip(FOOTPRINT_LANGUAGE_LABEL_X, categories, strict=True)
    )


def render_language_segments(categories: Sequence[LanguageCategory]) -> str:
    widths = allocate_widths([category.count for category in categories], FOOTPRINT_BAR_WIDTH)
    offsets = [sum(widths[:index]) for index in range(len(widths))]
    return "\n        ".join(
        f'<rect x="{offset}" width="{width}" height="16" fill="var(--{color})"/>'
        for offset, width, color in zip(
            offsets,
            widths,
            FOOTPRINT_LANGUAGE_COLORS,
            strict=True,
        )
    )


def render_footprint(
    profile: GitHubProfile,
    template: str,
) -> str:
    original = [repository for repository in profile.repositories if not repository.is_fork]
    categories = language_categories(profile)
    stars = sum(repository.stars for repository in original)
    forks = sum(repository.forks for repository in original)

    return Template(template).substitute(
        public_repositories=f"{profile.public_repositories:,}",
        stars=f"{stars:,}",
        forks=f"{forks:,}",
        followers=f"{profile.followers:,}",
        leading_language=escape_xml(categories[0].name),
        language_legend=render_language_legend(categories),
        language_segments=render_language_segments(categories),
        language_counts=" · ".join(str(category.count) for category in categories),
    )


def replace_section(document: str, start: str, end: str, content: str) -> str:
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f"Expected one marker pair: {start} … {end}")

    before, remainder = document.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n{content}\n{end}{after}"


def build_outputs(
    document: str,
    footprint_template: str,
    profile: GitHubProfile,
    writing: Sequence[WritingEntry],
) -> tuple[str, str]:
    updated_document = replace_section(
        document,
        REPOSITORIES_START,
        REPOSITORIES_END,
        render_repositories(featured_repository_signals(profile)),
    )
    updated_document = replace_section(
        updated_document,
        WRITING_START,
        WRITING_END,
        render_writing(writing),
    )
    footprint = render_footprint(profile, footprint_template)
    return updated_document, footprint


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--readme",
        type=Path,
        default=repository_root / "README.md",
        help="README file to update",
    )
    parser.add_argument(
        "--footprint",
        type=Path,
        default=repository_root / "github-metrics.svg",
        help="generated engineering footprint",
    )
    parser.add_argument(
        "--footprint-template",
        type=Path,
        default=repository_root / "assets" / "github-metrics.template.svg",
        help="engineering footprint template",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether generated files would change without writing them",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail instead of preserving existing files when remote data is unavailable",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    document = args.readme.read_text(encoding="utf-8")
    current_footprint = args.footprint.read_text(encoding="utf-8")
    footprint_template = args.footprint_template.read_text(encoding="utf-8")

    try:
        profile = fetch_github_profile(os.environ.get("GITHUB_TOKEN"))
        writing = fetch_zenn_writing()
    except (
        ElementTree.ParseError,
        json.JSONDecodeError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        print(f"Profile data fetch failed: {error}", file=sys.stderr)
        return 2 if args.strict else 0

    try:
        updated_document, updated_footprint = build_outputs(
            document,
            footprint_template,
            profile,
            writing,
        )
    except (KeyError, TypeError, ValueError) as error:
        print(f"Profile generation failed: {error}", file=sys.stderr)
        return 3

    changed = [
        name
        for name, before, after in (
            ("README.md", document, updated_document),
            ("github-metrics.svg", current_footprint, updated_footprint),
        )
        if before != after
    ]
    if not changed:
        print("Profile data is already current.")
        return 0
    if args.check:
        print(f"Profile data would change: {', '.join(changed)}")
        return 1

    atomic_write_text(args.footprint, updated_footprint)
    atomic_write_text(args.readme, updated_document)
    print(f"Profile data updated: {', '.join(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
