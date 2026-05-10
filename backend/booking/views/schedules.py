from __future__ import annotations

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET

from ..models import LiveSchedule
from ..services.roles import is_backoffice_admin


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
    profile = getattr(user, "profile", None)
    profile_role = getattr(profile, "role", "user")
    range_start = _to_aware_dt(request.GET.get("start"))
    range_end = _to_aware_dt(request.GET.get("end"))

    qs = LiveSchedule.objects.select_related("user", "user__profile")
    is_admin = is_backoffice_admin(user)

    if is_admin:
        pass
    elif profile_role == "brand":
        brand_id = getattr(profile, "brand_id", None)
        qs = qs.filter(brand_id=brand_id) if brand_id else qs.none()
    else:
        qs = qs.filter(user_id=user.id)

    if range_start and range_end:
        qs = qs.filter(start_time__lt=range_end, end_time__gt=range_start)
    elif range_start:
        qs = qs.filter(end_time__gt=range_start)
    elif range_end:
        qs = qs.filter(start_time__lt=range_end)

    events = []
    for s in qs.only(
        "id",
        "title",
        "start_time",
        "end_time",
        "is_cancelled",
        "is_verified",
        "user_id",
        "user__id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__profile__profile_image",
        "user__profile__photo_url",
    ):
        host = s.user
        host_name = (
            (f"{host.first_name} {host.last_name}".strip())
            or host.get_username()
            or "Host"
        )

        icon_url = ""
        try:
            host_profile = getattr(host, "profile", None)
            if host_profile and host_profile.profile_image:
                icon_url = host_profile.profile_image.url
            elif host_profile:
                icon_url = host_profile.photo_url or ""
        except Exception:
            icon_url = ""

        is_editable = bool(
            is_admin
            or (profile_role != "brand" and host.id == user.id)
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
