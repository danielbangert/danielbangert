#!/usr/bin/env python3
"""Fetch recent Bluesky posts via the public API and write their text into
README.md between the BLUESKY-POSTS markers. Standard library only; no auth
token required (uses the unauthenticated public AppView endpoint).
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HANDLE = "danielbangert.bsky.social"
MAX_ITEMS = 3                       # how many recent posts to show
README = Path("README.md")
START = "<!-- BLUESKY-POSTS:START -->"
END = "<!-- BLUESKY-POSTS:END -->"
API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bluesky-readme-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def post_url(uri):
    # uri looks like: at://did:plc:xxxx/app.bsky.feed.post/<rkey>
    rkey = uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{HANDLE}/post/{rkey}"


def fmt_date(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d %b %Y")
    except Exception:
        return ""


def main():
    query = urllib.parse.urlencode(
        {"actor": HANDLE, "limit": 30, "filter": "posts_no_replies"}
    )
    data = fetch_json(f"{API}?{query}")

    entries = []
    for item in data.get("feed", []):
        if item.get("reason"):        # skip reposts, keep original posts
            continue
        post = item.get("post", {})
        record = post.get("record", {})
        text = (record.get("text") or "").strip()
        if not text:
            continue
        entries.append(
            (text, fmt_date(record.get("createdAt", "")), post_url(post.get("uri", "")))
        )
        if len(entries) >= MAX_ITEMS:
            break

    blocks = []
    for text, date, url in entries:
        quoted = "\n".join("> " + line for line in text.splitlines())
        meta = " · ".join(x for x in [date, f"[View on Bluesky]({url})"] if x)
        blocks.append(f"{quoted}\n>\n> {meta}")
    body = "\n\n".join(blocks) if blocks else "_No recent posts._"

    content = README.read_text(encoding="utf-8")
    replacement = f"{START}\n{body}\n{END}"
    if START in content and END in content:
        content = re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            lambda _: replacement,
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.rstrip() + f"\n\n{replacement}\n"
    README.write_text(content, encoding="utf-8")
    print(f"Wrote {len(entries)} Bluesky post(s) to README.md")


if __name__ == "__main__":
    main()
