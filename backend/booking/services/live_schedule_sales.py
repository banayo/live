"""Enter sales + slip images for pending (รอยืนยัน) live schedules."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.http import HttpRequest

from ..models import LiveSchedule, LiveScheduleImage, User
from .live_schedule_image import (
    MAX_IMAGES_PER_SCHEDULE,
    MAX_IMAGE_BYTES,
    is_allowed_schedule_image_upload,
    resolve_schedule_image_url,
)
from .user_live_booking import get_user_live_schedule_for_edit


def serialize_schedule_for_sales(request: HttpRequest, schedule: LiveSchedule) -> dict[str, Any]:
    images = []
    for img in schedule.images.all().order_by("order", "pk"):
        url = resolve_schedule_image_url(request, img)
        if not url:
            continue
        images.append({"id": img.id, "url": url, "order": img.order})
    read_only = bool(schedule.is_verified or schedule.is_cancelled)
    return {
        "id": schedule.id,
        "title": schedule.title,
        "start": schedule.start_time.isoformat(),
        "end": schedule.end_time.isoformat(),
        "is_verified": schedule.is_verified,
        "is_cancelled": schedule.is_cancelled,
        "read_only": read_only,
        "total_raw": str(schedule.total_raw),
        "view_count": schedule.view_count,
        "images": images,
    }


def submit_user_live_schedule_sales(
    *,
    request: HttpRequest,
    user: User,
    schedule_id: int,
    total_raw: str | float | Decimal,
    view_count: int,
    new_files: list,
    remove_image_ids: list[int] | None = None,
) -> tuple[LiveSchedule | None, str | None]:
    """
    Save sales figures and up to 3 slip images for a pending schedule,
    then mark the schedule verified (locks further user edits).

    Returns (schedule, None) or (None, error_code).
    """
    schedule, err = get_user_live_schedule_for_edit(user=user, schedule_id=schedule_id)
    if err or schedule is None:
        return None, err or "not_found"

    try:
        raw_dec = Decimal(str(total_raw))
    except (InvalidOperation, TypeError, ValueError):
        return None, "invalid_values"
    if raw_dec < 0:
        return None, "invalid_values"

    try:
        views = int(view_count)
    except (TypeError, ValueError):
        return None, "invalid_values"
    if views < 0:
        return None, "invalid_values"

    remove_ids: set[int] = set()
    if remove_image_ids:
        for rid in remove_image_ids:
            try:
                remove_ids.add(int(rid))
            except (TypeError, ValueError):
                return None, "invalid_image_id"

    validated_files: list = []
    for f in new_files or []:
        if not f:
            continue
        if not is_allowed_schedule_image_upload(f):
            return None, "invalid_image"
        size = int(getattr(f, "size", 0) or 0)
        if size <= 0 or size > MAX_IMAGE_BYTES:
            return None, "invalid_image"
        validated_files.append(f)

    with transaction.atomic():
        locked = (
            LiveSchedule.objects.select_for_update()
            .filter(pk=schedule_id, user_id=user.id)
            .first()
        )
        if not locked:
            return None, "not_found"
        if locked.is_cancelled or locked.is_verified:
            return None, "not_editable"

        if remove_ids:
            locked.images.filter(pk__in=remove_ids, live_schedule_id=locked.pk).delete()

        existing_count = locked.images.count()
        if existing_count + len(validated_files) > MAX_IMAGES_PER_SCHEDULE:
            return None, "too_many_images"

        next_order = (
            locked.images.order_by("-order").values_list("order", flat=True).first() or -1
        )
        for f in validated_files:
            next_order += 1
            LiveScheduleImage.objects.create(
                live_schedule=locked,
                image=f,
                order=next_order,
            )

        locked.total_raw = raw_dec
        locked.view_count = views
        locked.is_verified = True
        locked.edited_by = user
        locked.save(
            update_fields=["total_raw", "view_count", "is_verified", "edited_by", "updated_at"]
        )

    schedule = LiveSchedule.objects.prefetch_related("images").get(pk=schedule_id)
    return schedule, None
