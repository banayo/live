"""Single place for "file avatar first, then external URL" resolution."""

from __future__ import annotations

import os

from django.http import HttpRequest

from ..models import Profile


def resolve_profile_avatar_url(request: HttpRequest, profile: Profile | None) -> str:
    """
    Prefer uploaded Profile.profile_image; otherwise Profile.photo_url (e.g. LINE CDN).

    Returns an absolute URL when the file field exposes a relative MEDIA path.
    """
    if profile is None:
        return ""
    try:
        f = getattr(profile, "profile_image", None)
        name = str(getattr(f, "name", "") or "").strip()
        if name:
            try:
                rel = str(f.url)
            except ValueError:
                rel = ""
            if rel:
                # Bust browser cache (including cached 404s) using file mtime when available.
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
                # Root-relative: same host as the browser page (avoids wrong Host/scheme from proxied API).
                if rel.startswith("/"):
                    if cache_bust and "?" not in rel:
                        return f"{rel}?{cache_bust}"
                    return rel
                abs_url = request.build_absolute_uri(rel)
                if cache_bust and "?" not in abs_url:
                    return f"{abs_url}?{cache_bust}"
                return abs_url
    except Exception:
        pass
    return str(getattr(profile, "photo_url", "") or "").strip()
