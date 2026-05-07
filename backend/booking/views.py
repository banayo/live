from __future__ import annotations

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET

from .models import LiveSchedule


def _to_aware_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = parse_datetime(value)
    if not dt:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


@require_GET
@login_required
def live_schedule_feed(request):
    """
    FullCalendar events feed.

    Query params (FullCalendar standard):
      - start: ISO datetime (range start)
      - end: ISO datetime (range end)
    """
    user = request.user
    range_start = _to_aware_dt(request.GET.get("start"))
    range_end = _to_aware_dt(request.GET.get("end"))

    qs = LiveSchedule.objects.select_related("user", "brand", "channel")

    if getattr(user, "is_admin_role", False):
        pass  # all schedules
    elif getattr(user, "is_mkt", False):
        qs = qs.filter(mkts=user)
    else:
        qs = qs.filter(user_id=user.id)

    # Overlap filter: event intersects requested range.
    if range_start and range_end:
        qs = qs.filter(start_time__lt=range_end, end_time__gt=range_start)
    elif range_start:
        qs = qs.filter(end_time__gt=range_start)
    elif range_end:
        qs = qs.filter(start_time__lt=range_end)

    # Keep payload small: only build what FullCalendar needs.
    events = []
    for s in qs.only(
        "id",
        "title",
        "start_time",
        "end_time",
        "is_cancelled",
        "is_verified",
        "user__id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__profile_image",
        "user__role",
    ):
        host = s.user
        host_name = (
            (f"{host.first_name} {host.last_name}".strip())
            or host.get_username()
            or "Host"
        )

        icon_url = ""
        try:
            if host.profile_image:
                icon_url = host.profile_image.url
        except Exception:
            icon_url = ""

        is_editable = bool(
            getattr(user, "is_admin_role", False)
            or (not getattr(user, "is_mkt", False) and host.id == user.id)
        )

        events.append(
            {
                "id": str(s.id),
                "title": s.title,
                "start": s.start_time.isoformat(),
                "end": s.end_time.isoformat(),
                "allDay": False,
                "editable": is_editable,
                "classNames": ["is-cancelled"] if s.is_cancelled else [],
                "extendedProps": {
                    "hostId": host.id,
                    "hostName": host_name,
                    "icon": icon_url,
                    "isVerified": s.is_verified,
                    "isCancelled": s.is_cancelled,
                },
            }
        )

    return JsonResponse(events, safe=False)

