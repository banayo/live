from __future__ import annotations

from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from ..services.live_schedule_sales import (
    serialize_schedule_for_sales,
    submit_user_live_schedule_sales,
)
from ..services.user_live_booking import get_user_live_schedule_for_view


def _json_error(message: str, *, status: int, code: str | None = None) -> JsonResponse:
    payload: dict[str, Any] = {"message": message}
    if code:
        payload["error"] = code
    return JsonResponse(payload, status=status)


@require_GET
def user_live_schedule_sales_get(request: HttpRequest, schedule_id: int) -> JsonResponse:
    """Load pending schedule + existing slip images for enter-sales."""
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")

    schedule, err = get_user_live_schedule_for_view(user=request.user, schedule_id=schedule_id)
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

    schedule = type(schedule).objects.prefetch_related("images").get(pk=schedule.pk)
    return JsonResponse(serialize_schedule_for_sales(request, schedule))


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def user_live_schedule_sales_submit(request: HttpRequest, schedule_id: int) -> JsonResponse:
    """Save sales (multipart): total_raw, view_count, images (max 3 total), remove_image_ids."""
    if request.method == "OPTIONS":
        return JsonResponse({})

    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")

    total_raw = request.POST.get("total_raw", "")
    view_count_raw = request.POST.get("view_count", "")

    new_files = list(request.FILES.getlist("images"))
    if not new_files:
        new_files = list(request.FILES.getlist("images[]"))

    remove_ids: list[int] = []
    for raw in request.POST.getlist("remove_image_ids"):
        try:
            remove_ids.append(int(raw))
        except (TypeError, ValueError):
            return _json_error("Invalid image id", status=400, code="invalid_image_id")

    try:
        view_count = int(view_count_raw)
    except (TypeError, ValueError):
        return _json_error("Invalid numeric values", status=400, code="invalid_values")

    schedule, err = submit_user_live_schedule_sales(
        request=request,
        user=request.user,
        schedule_id=schedule_id,
        total_raw=total_raw,
        view_count=view_count,
        new_files=new_files,
        remove_image_ids=remove_ids or None,
    )
    if err:
        status_map = {
            "not_verified": 403,
            "use_backoffice": 403,
            "no_profile": 400,
            "not_found": 404,
            "not_editable": 403,
            "invalid_values": 400,
            "invalid_image": 400,
            "invalid_image_id": 400,
            "too_many_images": 400,
        }
        messages = {
            "not_editable": "รายการยืนยันหรือยกเลิกแล้ว — กรอกยอดได้เฉพาะรอบที่รอยืนยัน",
            "too_many_images": "อัปโหลดรูปได้สูงสุด 3 ภาพ",
            "invalid_image": "ไฟล์รูปไม่ถูกต้องหรือใหญ่เกินไป",
        }
        status = status_map.get(err, 400)
        return _json_error(messages.get(err, "Cannot save sales"), status=status, code=err)

    return JsonResponse(
        {
            "ok": True,
            "id": schedule.id,
            "redirect_url": "/live-history",
            **serialize_schedule_for_sales(request, schedule),
        },
        status=200,
    )
