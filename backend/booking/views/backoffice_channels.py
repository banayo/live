from __future__ import annotations

import re
from typing import Any

from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..models import Channel
from ..services.channel_icon import resolve_channel_icon_url
from ..services.roles import is_backoffice_admin

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_MAX_ICON_BYTES = 5 * 1024 * 1024


def _json_error(message: str, *, status: int, code: str | None = None) -> JsonResponse:
    payload: dict[str, Any] = {"message": message}
    if code:
        payload["error"] = code
    return JsonResponse(payload, status=status)


def _get_request_json(request: HttpRequest) -> dict[str, Any] | None:
    try:
        raw = request.body.decode("utf-8") if request.body else ""
        if not raw.strip():
            return {}
        data = __import__("json").loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _normalize_hex(value: Any) -> str:
    s = str(value or "").strip()
    if not s:
        return "#3788d8"
    if not s.startswith("#"):
        s = "#" + s
    if _HEX_RE.match(s):
        return s.lower()
    return "#3788d8"


def _channel_dict(request: HttpRequest, ch: Channel) -> dict[str, Any]:
    return {
        "id": ch.id,
        "name": ch.name,
        "code": ch.code,
        "color_hex": ch.color_hex or "#3788d8",
        "is_active": ch.is_active,
        "icon_url": resolve_channel_icon_url(request, ch),
    }


@require_GET
def backoffice_channels_list(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Unauthorized"}, status=401)
    if not is_backoffice_admin(request.user):
        return JsonResponse({"ok": False, "message": "Forbidden"}, status=403)

    rows = Channel.objects.order_by("name").all()
    channels = [_channel_dict(request, ch) for ch in rows]
    return JsonResponse({"ok": True, "channels": channels}, status=200)


def _normalize_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return True if value == 1 else False if value == 0 else None
    s = str(value).strip().lower()
    if s in {"true", "1", "yes", "on"}:
        return True
    if s in {"false", "0", "no", "off", ""}:
        return False
    return None


@csrf_exempt
@require_POST
def backoffice_channel_create(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")
    if not is_backoffice_admin(request.user):
        return _json_error("Forbidden", status=403, code="forbidden")

    is_multipart = (request.content_type or "").startswith("multipart/form-data")
    if is_multipart:
        data: dict[str, Any] = dict(request.POST.items())
        icon_file = request.FILES.get("icon")
    else:
        data = _get_request_json(request)
        if data is None:
            return _json_error("Invalid JSON body.", status=400, code="invalid_json")
        icon_file = None

    name = str(data.get("name") or "").strip()[:50]
    code = str(data.get("code") or "").strip()[:10]
    if not name or not code:
        return _json_error("ชื่อและรหัสย่อจำเป็น", status=400, code="missing_fields")

    color_hex = _normalize_hex(data.get("color_hex"))
    is_active = _normalize_optional_bool(data.get("is_active"))
    if is_active is None:
        is_active = True

    if icon_file is not None:
        ct = str(getattr(icon_file, "content_type", "") or "")
        if not ct.startswith("image/"):
            return _json_error("ไอคอนต้องเป็นไฟล์ภาพ", status=400, code="invalid_image")
        if icon_file.size > _MAX_ICON_BYTES:
            return _json_error("ไฟล์ใหญ่เกินไป (สูงสุด 5MB)", status=400, code="image_too_large")

    try:
        ch = Channel.objects.create(
            name=name,
            code=code,
            color_hex=color_hex,
            is_active=is_active,
            icon=icon_file if icon_file else None,
        )
    except IntegrityError:
        return _json_error("ชื่อหรือรหัสย่อซ้ำกับที่มีอยู่แล้ว", status=409, code="duplicate")

    return JsonResponse({"ok": True, "channel": _channel_dict(request, ch)}, status=201)


@csrf_exempt
@require_POST
def backoffice_channel_update(request: HttpRequest, channel_id: int) -> JsonResponse:
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")
    if not is_backoffice_admin(request.user):
        return _json_error("Forbidden", status=403, code="forbidden")

    is_multipart = (request.content_type or "").startswith("multipart/form-data")
    if is_multipart:
        data = dict(request.POST.items())
        icon_file = request.FILES.get("icon")
    else:
        data = _get_request_json(request)
        if data is None:
            return _json_error("Invalid JSON body.", status=400, code="invalid_json")
        icon_file = None

    if icon_file is not None:
        ct = str(getattr(icon_file, "content_type", "") or "")
        if not ct.startswith("image/"):
            return _json_error("ไอคอนต้องเป็นไฟล์ภาพ", status=400, code="invalid_image")
        if icon_file.size > _MAX_ICON_BYTES:
            return _json_error("ไฟล์ใหญ่เกินไป (สูงสุด 5MB)", status=400, code="image_too_large")

    with transaction.atomic():
        ch = Channel.objects.select_for_update().filter(pk=channel_id).first()
        if not ch:
            return _json_error("ไม่พบช่องทาง", status=404, code="not_found")

        update_fields: list[str] = []
        if "name" in data:
            n = str(data.get("name") or "").strip()[:50]
            if not n:
                return _json_error("ชื่อต้องไม่ว่าง", status=400, code="invalid_name")
            ch.name = n
            update_fields.append("name")
        if "code" in data:
            c = str(data.get("code") or "").strip()[:10]
            if not c:
                return _json_error("รหัสย่อต้องไม่ว่าง", status=400, code="invalid_code")
            ch.code = c
            update_fields.append("code")
        if "color_hex" in data:
            ch.color_hex = _normalize_hex(data.get("color_hex"))
            update_fields.append("color_hex")
        if "is_active" in data:
            b = _normalize_optional_bool(data.get("is_active"))
            if b is not None:
                ch.is_active = b
                update_fields.append("is_active")
        if icon_file is not None:
            ch.icon = icon_file
            update_fields.append("icon")

        if not update_fields:
            return JsonResponse({"ok": True, "channel": _channel_dict(request, ch)}, status=200)

        try:
            ch.save(update_fields=update_fields)
        except IntegrityError:
            return _json_error("ชื่อหรือรหัสย่อซ้ำกับที่มีอยู่แล้ว", status=409, code="duplicate")

    return JsonResponse({"ok": True, "channel": _channel_dict(request, ch)}, status=200)
