"""Resolve Channel.icon (ImageField) to a browser-usable URL."""

from __future__ import annotations

import os

from django.http import HttpRequest

from ..models import Channel


def resolve_channel_icon_url(request: HttpRequest, channel: Channel | None) -> str:
    """Return absolute or root-relative URL for uploaded icon, or empty string."""
    if channel is None:
        return ""
    try:
        f = getattr(channel, "icon", None)
        name = str(getattr(f, "name", "") or "").strip()
        if not name:
            return ""
        try:
            rel = str(f.url)
        except ValueError:
            return ""
        if not rel:
            return ""
        cache_bust = ""
        try:
            path = str(getattr(f, "path", "") or "").strip()
            if path and os.path.exists(path):
                cache_bust = f"v={int(os.path.getmtime(path))}"
        except Exception:
            cache_bust = ""

        if rel.startswith(("http://", "https://")):
            if cache_bust and "?" not in rel:
                return f"{rel}?{cache_bust}"
            return rel
        if rel.startswith("/"):
            if cache_bust and "?" not in rel:
                return f"{rel}?{cache_bust}"
            return rel
        abs_url = request.build_absolute_uri(rel)
        if cache_bust and "?" not in abs_url:
            return f"{abs_url}?{cache_bust}"
        return abs_url
    except Exception:
        return ""
