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

    qs = LiveSchedule.objects.select_related("host")

    # Role filtering (phase A: no Brand model yet)
    if getattr(user, "is_admin_role", False):
        pass  # all schedules
    elif getattr(user, "is_mkt", False):
        pass  # MKT sees all (read-only handled by frontend)
    else:
        qs = qs.filter(host_id=user.id)

    # Overlap filter: event intersects requested range.
    if range_start and range_end:
        qs = qs.filter(start__lt=range_end, end__gt=range_start)
    elif range_start:
        qs = qs.filter(end__gt=range_start)
    elif range_end:
        qs = qs.filter(start__lt=range_end)

    # Keep payload small: only build what FullCalendar needs.
    events = []
    for s in qs.only(
        "id",
        "title",
        "start",
        "end",
        "all_day",
        "host__id",
        "host__username",
        "host__first_name",
        "host__last_name",
        "host__profile_image",
        "host__role",
    ):
        host = s.host
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
                "start": s.start.isoformat(),
                "end": s.end.isoformat(),
                "allDay": s.all_day,
                "editable": is_editable,
                "extendedProps": {
                    "hostId": host.id,
                    "hostName": host_name,
                    "icon": icon_url,
                },
            }
        )

    return JsonResponse(events, safe=False)

