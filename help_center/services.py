from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


YOUTUBE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def extract_youtube_video_id(url: str) -> str | None:
    """Return an 11-char YouTube video ID from common URL formats."""
    if not url:
        return None
    raw = url.strip()
    if YOUTUBE_ID_RE.fullmatch(raw):
        return raw

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower().replace("www.", "")

    if host in ("youtu.be",):
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate if YOUTUBE_ID_RE.fullmatch(candidate or "") else None

    if host in ("youtube.com", "m.youtube.com", "music.youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            vid = (qs.get("v") or [None])[0]
            return vid if vid and YOUTUBE_ID_RE.fullmatch(vid) else None
        for prefix in ("/embed/", "/shorts/", "/live/"):
            if parsed.path.startswith(prefix):
                candidate = parsed.path[len(prefix) :].split("/")[0]
                return candidate if YOUTUBE_ID_RE.fullmatch(candidate or "") else None
    return None


def youtube_embed_url(video_id: str) -> str:
    return f"https://www.youtube-nocookie.com/embed/{video_id}"


def youtube_thumbnail_url(video_id: str) -> str:
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
