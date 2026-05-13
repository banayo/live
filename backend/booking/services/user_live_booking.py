from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction

from ..models import Brand, Channel, LiveSchedule
from ..services.roles import is_backoffice_admin


def _book_live_allowed_brands_queryset(profile) -> Any:
    """Active brands the user may attach to a self-serve live booking."""
    if not profile:
        return Brand.objects.none()
    return Brand.objects.filter(is_active=True).order_by("name")


def book_live_brand_options_list(user: User) -> list[dict[str, Any]]:
    """Serialize allowed brands for GET /api/user/book-live-options/."""
    profile = getattr(user, "profile", None)
    qs = _book_live_allowed_brands_queryset(profile)
    return list(qs[:80].values("id", "name"))


def _resolve_brand_for_live_schedule(profile, brand_id: int | None) -> tuple[Brand | None, str | None]:
    """
    Pick LiveSchedule.brand from allowed set and optional client brand_id.

    Returns (brand, None) or (None, error_code).
    """
    allowed = list(_book_live_allowed_brands_queryset(profile)[:80])
    if not allowed:
        return None, None

    allowed_ids = {b.pk for b in allowed}
    if len(allowed) == 1:
        only = allowed[0]
        if brand_id is not None:
            try:
                bid = int(brand_id)
            except (TypeError, ValueError):
                return None, "invalid_brand"
            if bid != only.pk:
                return None, "invalid_brand"
        return only, None

    if brand_id is None:
        return None, "missing_brand"
    try:
        bid = int(brand_id)
    except (TypeError, ValueError):
        return None, "invalid_brand"
    brand = Brand.objects.filter(pk=bid, is_active=True, pk__in=allowed_ids).first()
    if not brand:
        return None, "invalid_brand"
    return brand, None


def create_user_live_schedule(
    *,
    user: User,
    title: str,
    start_time: datetime,
    end_time: datetime,
    note: str = "",
    channel_id: int | None = None,
    brand_id: int | None = None,
) -> tuple[LiveSchedule | None, str | None]:
    """
    Create a pending LiveSchedule for the logged-in host.

    Returns (instance, None) on success, or (None, error_code) on failure.
    """
    profile = getattr(user, "profile", None)
    if not profile:
        return None, "no_profile"
    if not profile.is_verified:
        return None, "not_verified"
    if is_backoffice_admin(user):
        return None, "use_backoffice"

    clean_title = (title or "").strip()
    if not clean_title or len(clean_title) > 200:
        return None, "invalid_title"

    if start_time >= end_time:
        return None, "invalid_range"
    if (end_time - start_time) < timedelta(minutes=30):
        return None, "invalid_range"

    brand, brand_err = _resolve_brand_for_live_schedule(profile, brand_id)
    if brand_err:
        return None, brand_err

    channel = None
    if channel_id is not None:
        channel = Channel.objects.filter(pk=int(channel_id), is_active=True).first()
        if not channel:
            return None, "invalid_channel"

    with transaction.atomic():
        schedule = LiveSchedule.objects.create(
            user=user,
            title=clean_title,
            brand=brand,
            channel=channel,
            start_time=start_time,
            end_time=end_time,
            note=(note or "").strip() or "",
            is_verified=False,
            is_cancelled=False,
        )

    return schedule, None
