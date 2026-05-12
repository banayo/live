from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..models import Brand
from ..services.roles import is_backoffice_admin


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


def _brand_dict(brand: Brand) -> dict[str, Any]:
    return {"id": brand.id, "name": brand.name, "is_active": brand.is_active}


@require_GET
def backoffice_brands_list(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Unauthorized"}, status=401)
    if not is_backoffice_admin(request.user):
        return JsonResponse({"ok": False, "message": "Forbidden"}, status=403)

    rows = Brand.objects.order_by("name").values("id", "name", "is_active")
    brands = [
        {"id": b["id"], "name": b["name"], "is_active": bool(b.get("is_active"))}
        for b in rows
    ]
    return JsonResponse({"ok": True, "brands": brands}, status=200)


@csrf_exempt
@require_POST
def backoffice_brand_create(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")
    if not is_backoffice_admin(request.user):
        return _json_error("Forbidden", status=403, code="forbidden")

    data = _get_request_json(request)
    if data is None:
        return _json_error("Invalid JSON body.", status=400, code="invalid_json")

    name = str(data.get("name") or "").strip()[:100]
    if not name:
        return _json_error("ชื่อแบรนด์จำเป็น", status=400, code="missing_name")

    is_active = bool(data.get("is_active", True))

    try:
        brand = Brand.objects.create(name=name, is_active=is_active)
    except IntegrityError:
        return _json_error("ชื่อแบรนด์นี้มีอยู่แล้ว", status=409, code="name_taken")

    return JsonResponse({"ok": True, "brand": _brand_dict(brand)}, status=201)


@csrf_exempt
@require_POST
def backoffice_brand_update(request: HttpRequest, brand_id: int) -> JsonResponse:
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")
    if not is_backoffice_admin(request.user):
        return _json_error("Forbidden", status=403, code="forbidden")

    data = _get_request_json(request)
    if data is None:
        return _json_error("Invalid JSON body.", status=400, code="invalid_json")

    with transaction.atomic():
        brand = Brand.objects.select_for_update().filter(pk=brand_id).first()
        if not brand:
            return _json_error("ไม่พบแบรนด์", status=404, code="not_found")

        update_fields: list[str] = []
        if "name" in data:
            n = str(data.get("name") or "").strip()[:100]
            if not n:
                return _json_error("ชื่อแบรนด์ต้องไม่ว่าง", status=400, code="invalid_name")
            brand.name = n
            update_fields.append("name")
        if "is_active" in data:
            brand.is_active = bool(data.get("is_active"))
            update_fields.append("is_active")

        if not update_fields:
            return JsonResponse({"ok": True, "brand": _brand_dict(brand)}, status=200)

        try:
            brand.save(update_fields=update_fields)
        except IntegrityError:
            return _json_error("ชื่อแบรนด์นี้มีอยู่แล้ว", status=409, code="name_taken")

    return JsonResponse({"ok": True, "brand": _brand_dict(brand)}, status=200)
