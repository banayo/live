"""LiveScheduleImage upload helpers."""

from __future__ import annotations

import os

from django.http import HttpRequest

from ..models import LiveScheduleImage

_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".heif", ".avif")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGES_PER_SCHEDULE = 3


def is_allowed_schedule_image_upload(image_file) -> bool:
    """Accept image/* MIME or a known image extension on the filename."""
    ct = str(getattr(image_file, "content_type", "") or "").strip().lower()
    if ct.startswith("image/"):
        return True
    name = str(getattr(image_file, "name", "") or "").strip().lower()
    return bool(name) and name.endswith(_IMAGE_EXT)


def resolve_schedule_image_url(request: HttpRequest, row: LiveScheduleImage | None) -> str:
    if row is None:
        return ""
    try:
        f = getattr(row, "image", None)
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
