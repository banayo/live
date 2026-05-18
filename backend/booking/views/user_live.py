from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ..models import Channel
from ..services.roles import is_backoffice_admin
from ..services.user_live_booking import (
    book_live_brand_options_list,
    create_user_live_schedule,
    get_user_live_schedule_for_edit,
    get_user_live_schedule_for_view,
    update_user_live_schedule,
)


def _json_error(message: str, *, status: int, code: str | None = None) -> JsonResponse:
    payload: dict[str, Any] = {"message": message}
    if code:
        payload["error"] = code
    return JsonResponse(payload, status=status)


def _parse_json(request: HttpRequest) -> dict[str, Any] | None:
    try:
        raw = request.body.decode("utf-8") if request.body else ""
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


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
def user_book_live_options(request: HttpRequest) -> JsonResponse:
    """Active channels and bookable brands for the Book Live form (authenticated users)."""
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")

    profile = getattr(request.user, "profile", None)
    if not profile or not profile.is_verified:
        return _json_error("Not verified", status=403, code="not_verified")

    if is_backoffice_admin(request.user):
        return JsonResponse({"channels": [], "brands": []})

    channels = list(
        Channel.objects.filter(is_active=True)
        .order_by("name")
        .values("id", "name", "code")[:80]
    )
    brands = book_live_brand_options_list(request.user)
    return JsonResponse({"channels": channels, "brands": brands})


@csrf_exempt
@require_POST
def user_live_schedule_create(request: HttpRequest) -> JsonResponse:
    """Create a Live schedule for the current verified user (or brand host)."""
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")

    body = _parse_json(request)
    if body is None:
        return _json_error("Invalid JSON", status=400, code="invalid_json")

    title = str(body.get("title") or "")
    start = _to_aware_dt(str(body.get("start") or "").strip() or None)
    end = _to_aware_dt(str(body.get("end") or "").strip() or None)
    note = str(body.get("note") or "")

    raw_ch = body.get("channel_id")
    channel_id: int | None = None
    if raw_ch is not None and str(raw_ch).strip() != "":
        try:
            channel_id = int(raw_ch)
        except (TypeError, ValueError):
            return _json_error("Invalid channel", status=400, code="invalid_channel")

    raw_brand = body.get("brand_id")
    brand_id: int | None = None
    if raw_brand is not None and str(raw_brand).strip() != "":
        try:
            brand_id = int(raw_brand)
        except (TypeError, ValueError):
            return _json_error("Invalid brand", status=400, code="invalid_brand")

    if not start or not end:
        return _json_error("Missing start or end", status=400, code="missing_times")

    schedule, err = create_user_live_schedule(
        user=request.user,
        title=title,
        start_time=start,
        end_time=end,
        note=note,
        channel_id=channel_id,
        brand_id=brand_id,
    )
    if err:
        status_map = {
            "not_verified": 403,
            "use_backoffice": 403,
            "no_profile": 400,
            "invalid_title": 400,
            "invalid_range": 400,
            "invalid_channel": 400,
            "invalid_brand": 400,
            "missing_brand": 400,
        }
        status = status_map.get(err, 400)
        return _json_error("Cannot create schedule", status=status, code=err)

    return JsonResponse(
        {
            "ok": True,
            "id": schedule.id,
            "redirect_url": "/dashboard",
        },
        status=201,
    )


def _serialize_schedule_for_user(schedule) -> dict[str, Any]:
    return {
        "id": schedule.id,
        "title": schedule.title,
        "start": schedule.start_time.isoformat(),
        "end": schedule.end_time.isoformat(),
        "note": schedule.note or "",
        "brand_id": schedule.brand_id,
        "channel_id": schedule.channel_id,
        "is_verified": schedule.is_verified,
        "is_cancelled": schedule.is_cancelled,
    }


@csrf_exempt
@require_http_methods(["GET", "PATCH", "OPTIONS"])
def user_live_schedule_detail(request: HttpRequest, schedule_id: int) -> JsonResponse:
    """Read or update one Live schedule (owner, pending only for mutation)."""
    if request.method == "OPTIONS":
        return JsonResponse({})

    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")

    if request.method == "GET":
        schedule, err = get_user_live_schedule_for_view(
            user=request.user, schedule_id=schedule_id
        )
        if err == "no_profile":
            return _json_error("No profile", status=400, code=err)
        if err == "not_found":
            return _json_error("Not found", status=404, code=err)
        if err == "not_verified":
            return _json_error("Not verified", status=403, code=err)
        if err == "use_backoffice":
            return _json_error("Use backoffice", status=403, code=err)
        if err or schedule is None:
            return _json_error("Cannot load schedule", status=400, code=err or "load_failed")
        return JsonResponse(_serialize_schedule_for_user(schedule))

    # PATCH
    body = _parse_json(request)
    if body is None:
        return _json_error("Invalid JSON", status=400, code="invalid_json")

    # For sales entry, we might not send title/start/end. 
    # But the service requires them currently. 
    # Let's load the current values if they are missing from body.
    schedule, err = get_user_live_schedule_for_edit(user=request.user, schedule_id=schedule_id)
    if err:
        status_map = {"not_found": 404, "not_editable": 403, "not_verified": 403}
        return _json_error("Cannot load schedule", status=status_map.get(err, 400), code=err)

    title = str(body.get("title") if "title" in body else schedule.title)
    start = _to_aware_dt(str(body.get("start"))) if "start" in body else schedule.start_time
    end = _to_aware_dt(str(body.get("end"))) if "end" in body else schedule.end_time
    note = str(body.get("note") if "note" in body else (schedule.note or ""))

    channel_id = schedule.channel_id
    if "channel_id" in body:
        raw_ch = body.get("channel_id")
        if raw_ch is not None and str(raw_ch).strip() != "":
            try:
                channel_id = int(raw_ch)
            except (TypeError, ValueError):
                return _json_error("Invalid channel", status=400, code="invalid_channel")
        else:
            channel_id = None

    brand_id = schedule.brand_id
    if "brand_id" in body:
        raw_brand = body.get("brand_id")
        if raw_brand is not None and str(raw_brand).strip() != "":
            try:
                brand_id = int(raw_brand)
            except (TypeError, ValueError):
                return _json_error("Invalid brand", status=400, code="invalid_brand")
        else:
            brand_id = None

    if not start or not end:
        return _json_error("Missing start or end", status=400, code="missing_times")

    schedule, err = update_user_live_schedule(
        schedule_id=schedule_id,
        user=request.user,
        title=title,
        start_time=start,
        end_time=end,
        note=note,
        channel_id=channel_id,
        brand_id=brand_id,
    )
    if err:
        status_map = {
            "not_verified": 403,
            "use_backoffice": 403,
            "no_profile": 400,
            "invalid_title": 400,
            "invalid_range": 400,
            "invalid_channel": 400,
            "invalid_brand": 400,
            "missing_brand": 400,
            "not_found": 404,
            "not_editable": 403,
        }
        status = status_map.get(err, 400)
        return _json_error("Cannot update schedule", status=status, code=err)

    return JsonResponse(
        {
            "ok": True,
            "id": schedule.id,
            "redirect_url": "/live-history",
        },
        status=200,
    )
