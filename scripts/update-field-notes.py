#!/usr/bin/env python3
"""Update the Field Notes section in README.md from the sashwat.in RSS feed."""

from __future__ import annotations

import email.utils
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


README_PATH = Path(os.environ.get("README_PATH", "README.md"))
FEED_URL = os.environ.get("FIELD_NOTES_FEED_URL", "https://sashwat.in/feed.xml")
POST_LIMIT = int(os.environ.get("FIELD_NOTES_LIMIT", "3"))
START_MARKER = "<!-- FIELD_NOTES:START -->"
END_MARKER = "<!-- FIELD_NOTES:END -->"


@dataclass(frozen=True)
class Post:
    title: str
    link: str
    description: str
    published: str
    categories: tuple[str, ...]


def text(node: ET.Element, name: str) -> str:
    child = node.find(name)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text.strip())


def format_date(value: str) -> str:
    if not value:
        return ""

    parsed = email.utils.parsedate_to_datetime(value)
    return datetime.strftime(parsed, "%b %-d, %Y")


def fetch_posts() -> list[Post]:
    request = urllib.request.Request(
        FEED_URL,
        headers={"User-Agent": "sashuu69-profile-readme-updater/1.0"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        feed = response.read()

    root = ET.fromstring(feed)
    posts: list[Post] = []

    for item in root.findall("./channel/item")[:POST_LIMIT]:
        categories = tuple(
            html.unescape(category.text.strip())
            for category in item.findall("category")
            if category.text and category.text.strip()
        )
        posts.append(
            Post(
                title=text(item, "title"),
                link=text(item, "link"),
                description=text(item, "description"),
                published=format_date(text(item, "pubDate")),
                categories=categories,
            )
        )

    return posts


def render(posts: list[Post]) -> str:
    if not posts:
        return "- Latest posts are available at [sashwat.in/blog](https://sashwat.in/blog/)."

    lines = []
    for post in posts:
        parts = [f"- [{post.title}]({post.link})"]
        if post.description:
            parts.append(f"- {post.description}")
        if post.published:
            parts.append(f"_{post.published}_")
        if post.categories:
            parts.extend(f"`{category}`" for category in post.categories)
        lines.append(" ".join(parts))

    return "\n".join(lines)


def update_readme(content: str, generated: str) -> str:
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{generated}\n{END_MARKER}"
    updated, count = pattern.subn(replacement, content)

    if count != 1:
        raise RuntimeError(
            f"Expected exactly one Field Notes section in {README_PATH}, found {count}."
        )

    return updated


def main() -> int:
    readme = README_PATH.read_text(encoding="utf-8")
    posts = fetch_posts()
    updated = update_readme(readme, render(posts))

    if updated != readme:
        README_PATH.write_text(updated, encoding="utf-8")
        print(f"Updated {README_PATH} with {len(posts)} post(s).")
    else:
        print(f"{README_PATH} is already up to date.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
