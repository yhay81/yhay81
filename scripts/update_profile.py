"""Refresh the small, useful live sections in the GitHub profile README.

The script intentionally uses only the Python standard library. It updates the
latest Zenn writing and shows WakaTime telemetry only when there is meaningful
activity, keeping the profile stable when an API is unavailable.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

ZENN_FEED_URL = "https://zenn.dev/yhay81/feed"
WAKATIME_STATS_URL = "https://wakatime.com/api/v1/users/current/stats/last_7_days"
USER_AGENT = "yhay81-profile-updater/1.0"

WRITING_START = "<!-- profile:writing:start -->"
WRITING_END = "<!-- profile:writing:end -->"
TELEMETRY_START = "<!-- profile:telemetry:start -->"
TELEMETRY_END = "<!-- profile:telemetry:end -->"


@dataclass(frozen=True)
class Post:
    title: str
    url: str
    published_at: datetime


def fetch_bytes(url: str, *, authorization: str | None = None) -> bytes:
    headers = {"Accept": "*/*", "User-Agent": USER_AGENT}
    if authorization:
        headers["Authorization"] = authorization
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def parse_zenn_feed(payload: bytes, *, limit: int = 3) -> list[Post]:
    root = ET.fromstring(payload)
    posts: list[Post] = []

    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        if title and url and published:
            posts.append(Post(title, url, parsedate_to_datetime(published)))

    if not posts:
        atom_namespace = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", atom_namespace):
            title = (entry.findtext("atom:title", default="", namespaces=atom_namespace)).strip()
            link = entry.find("atom:link", atom_namespace)
            url = (link.get("href") if link is not None else "") or ""
            published = (
                entry.findtext("atom:published", default="", namespaces=atom_namespace)
                or entry.findtext("atom:updated", default="", namespaces=atom_namespace)
            ).strip()
            if title and url and published:
                posts.append(Post(title, url, datetime.fromisoformat(published.replace("Z", "+00:00"))))

    posts.sort(key=lambda post: post.published_at, reverse=True)
    return posts[:limit]


def escape_markdown(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def render_writing(posts: list[Post]) -> str:
    return "\n".join(
        f"- [{escape_markdown(post.title)}]({post.url}) — {post.published_at:%Y-%m-%d}"
        for post in posts
    )


def render_telemetry(payload: dict[str, Any], *, minimum_seconds: float = 300) -> str:
    data = payload.get("data") or {}
    total_seconds = float(data.get("total_seconds") or 0)
    if total_seconds < minimum_seconds:
        return ""

    total = (
        data.get("human_readable_total_including_other_language")
        or data.get("human_readable_total")
        or f"{round(total_seconds / 3600, 1)} hrs"
    )
    languages = [
        language
        for language in (data.get("languages") or [])
        if float(language.get("percent") or 0) >= 1
    ][:5]
    language_summary = " · ".join(
        f"`{language.get('name', 'Other')}` {float(language.get('percent') or 0):.0f}%"
        for language in languages
    )

    lines = [
        "<details>",
        f"<summary><strong>Developer telemetry</strong> · last 7 days · {total}</summary>",
        "",
    ]
    if language_summary:
        lines.append(language_summary)
        lines.append("")
    lines.extend(
        [
            "<sub>Editor activity from WakaTime. Refreshed weekly and hidden when there is no meaningful activity.</sub>",
            "</details>",
        ]
    )
    return "\n".join(lines)


def replace_section(document: str, start: str, end: str, content: str) -> str:
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f"Expected one marker pair: {start} … {end}")

    before, remainder = document.split(start, 1)
    _, after = remainder.split(end, 1)
    body = f"\n{content}\n" if content else "\n"
    return f"{before}{start}{body}{end}{after}"


def waka_authorization(api_key: str) -> str:
    token = base64.b64encode(f"{api_key}:".encode()).decode()
    return f"Basic {token}"


def refresh(document: str, *, waka_api_key: str | None) -> tuple[str, list[str]]:
    updated = document
    messages: list[str] = []

    try:
        posts = parse_zenn_feed(fetch_bytes(ZENN_FEED_URL))
        if not posts:
            raise ValueError("Zenn feed contained no posts")
        updated = replace_section(updated, WRITING_START, WRITING_END, render_writing(posts))
        messages.append(f"Zenn: refreshed {len(posts)} entries")
    except (ET.ParseError, OSError, ValueError, urllib.error.URLError) as error:
        messages.append(f"Zenn: kept existing content ({error})")

    if waka_api_key:
        try:
            payload = json.loads(
                fetch_bytes(
                    WAKATIME_STATS_URL,
                    authorization=waka_authorization(waka_api_key),
                )
            )
            updated = replace_section(
                updated,
                TELEMETRY_START,
                TELEMETRY_END,
                render_telemetry(payload),
            )
            messages.append("WakaTime: refreshed telemetry")
        except (json.JSONDecodeError, OSError, ValueError, urllib.error.URLError) as error:
            messages.append(f"WakaTime: kept existing content ({error})")
    else:
        messages.append("WakaTime: skipped (WAKATIME_API_KEY is not set)")

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
    updated, messages = refresh(document, waka_api_key=os.environ.get("WAKATIME_API_KEY"))

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
