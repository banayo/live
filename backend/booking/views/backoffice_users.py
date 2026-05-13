from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..models import Profile, User
from ..services.profile_avatar import resolve_profile_avatar_url
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


def _normalize_optional_bool(value: Any) -> bool | None:
    """Accept bool/int 0–1/strings from JSON or multipart; unknown → omit (None)."""
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


_MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024


@require_GET
def backoffice_users_list(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Unauthorized"}, status=401)
    if not is_backoffice_admin(request.user):
        return JsonResponse({"ok": False, "message": "Forbidden"}, status=403)

    qs = (
        User.objects.select_related("profile")
        .order_by("-date_joined")
        .only(
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "date_joined",
            "profile__phone_number",
            "profile__role",
            "profile__is_verified",
            "profile__line_uid",
            "profile__kof",
            "profile__bank_account_number",
            "profile__bank_name",
            "profile__photo_url",
            "profile__profile_image",
        )
    )

    users: list[dict[str, Any]] = []
    for u in qs:
        profile = getattr(u, "profile", None)
        full_name = f"{u.first_name} {u.last_name}".strip() or u.get_username()
        line_uid_raw = getattr(profile, "line_uid", None)
        photo_url_raw = getattr(profile, "photo_url", None) or ""
        users.append(
            {
                "id": u.id,
                "username": u.get_username(),
                "name": full_name,
                "email": u.email or "",
                "phone_number": getattr(profile, "phone_number", "") or "",
                "kof": getattr(profile, "kof", "") or "",
                "bank_account_number": getattr(profile, "bank_account_number", "") or "",
                "bank_name": getattr(profile, "bank_name", "") or "",
                "line_uid": line_uid_raw or "",
                "photo_url": str(photo_url_raw).strip() if photo_url_raw else "",
                "avatar_url": resolve_profile_avatar_url(request, profile),
                "role": getattr(profile, "role", "user") or "user",
                "is_verified": bool(getattr(profile, "is_verified", False)),
                "line_connected": bool(line_uid_raw),
                "brand": None,
                "created_at": u.date_joined.isoformat() if u.date_joined else None,
            }
        )

    return JsonResponse({"ok": True, "users": users, "brands": []}, status=200)


@csrf_exempt
@require_POST
def backoffice_user_update(request: HttpRequest, user_id: int) -> JsonResponse:
    if not request.user.is_authenticated:
        return _json_error("Unauthorized", status=401, code="unauthorized")
    if not is_backoffice_admin(request.user):
        return _json_error("Forbidden", status=403, code="forbidden")

    is_multipart = (request.content_type or "").startswith("multipart/form-data")
    if is_multipart:
        data: dict[str, Any] = dict(request.POST.items())
    else:
        data = _get_request_json(request)
        if data is None:
            return _json_error("Invalid JSON body.", status=400, code="invalid_json")

    _role_raw = data.get("role", None)
    role = None
    if _role_raw is not None:
        role = str(_role_raw).strip() or None
    is_verified = _normalize_optional_bool(data.get("is_verified", None))

    name = data.get("name", None)
    email = data.get("email", None)
    phone_number = data.get("phone_number", None)
    kof = data.get("kof", None)
    bank_account_number = data.get("bank_account_number", None)
    bank_name = data.get("bank_name", None)
    photo_url = data.get("photo_url", None)
    line_uid = data.get("line_uid", None)
    profile_image_file = request.FILES.get("profile_image") if is_multipart else None
    if profile_image_file is not None:
        content_type = str(getattr(profile_image_file, "content_type", "") or "")
        if not content_type.startswith("image/"):
            return _json_error("รูปโปรไฟล์ต้องเป็นไฟล์ภาพ", status=400, code="invalid_image")
        if profile_image_file.size > _MAX_PROFILE_IMAGE_BYTES:
            return _json_error("รูปโปรไฟล์ใหญ่เกินไป (สูงสุด 5MB)", status=400, code="image_too_large")

    allowed_roles = {"admin", "brand", "user"}
    if role is not None and role not in allowed_roles:
        return _json_error("Invalid role.", status=400, code="invalid_role")

    if phone_number is not None:
        phone_number = str(phone_number).strip()[:15]
    if name is not None:
        name = str(name).strip()[:150]
    if email is not None:
        email = str(email).strip().lower()[:254]
    if kof is not None:
        kof = str(kof).strip()[:50]
    if bank_account_number is not None:
        bank_account_number = str(bank_account_number).strip()[:30]
    if bank_name is not None:
        bank_name = str(bank_name).strip()[:100]
    if photo_url is not None:
        photo_url = str(photo_url).strip()[:500]
    line_uid_normalized: str | None = None
    if line_uid is not None:
        raw_line = str(line_uid).strip()
        line_uid_normalized = raw_line[:255] if raw_line else None

    if line_uid is not None and line_uid_normalized:
        conflict = (
            Profile.objects.exclude(user_id=user_id)
            .exclude(Q(line_uid__isnull=True) | Q(line_uid=""))
            .filter(line_uid=line_uid_normalized)
            .exists()
        )
        if conflict:
            return _json_error("LINE UID already linked to another user.", status=409, code="line_uid_taken")

    with transaction.atomic():
        user = (
            User.objects.select_for_update()
            .filter(pk=user_id)
            .first()
        )
        if not user:
            return _json_error("User not found.", status=404, code="user_not_found")

        if email is not None:
            if email and User.objects.exclude(pk=user_id).filter(email__iexact=email).exists():
                return _json_error("อีเมลนี้ถูกใช้งานแล้ว", status=409, code="email_taken")

        try:
            profile = Profile.objects.select_for_update().get(user=user)
        except Profile.DoesNotExist:
            return _json_error("ไม่พบโปรไฟล์ของผู้ใช้คนนี้", status=404, code="missing_profile")

        update_fields: list[str] = []
        user_update_fields: list[str] = []

        if name is not None:
            # split to first_name / last_name for Django admin compatibility
            parts = [p for p in name.split(" ") if p]
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            user.first_name = first_name[:150]
            user.last_name = last_name[:150]
            user_update_fields.extend(["first_name", "last_name"])

        if email is not None:
            user.email = email
            user_update_fields.append("email")

        if role is not None:
            profile.role = role
            update_fields.append("role")
        if is_verified is not None:
            profile.is_verified = bool(is_verified)
            update_fields.append("is_verified")
        if phone_number is not None:
            profile.phone_number = phone_number
            update_fields.append("phone_number")
        if kof is not None:
            profile.kof = kof
            update_fields.append("kof")
        if bank_account_number is not None:
            profile.bank_account_number = bank_account_number
            update_fields.append("bank_account_number")
        if bank_name is not None:
            profile.bank_name = bank_name
            update_fields.append("bank_name")
        if photo_url is not None:
            profile.photo_url = photo_url if photo_url else None
            update_fields.append("photo_url")
        if line_uid is not None:
            profile.line_uid = line_uid_normalized
            update_fields.append("line_uid")
        if profile_image_file is not None:
            profile.profile_image = profile_image_file
            update_fields.append("profile_image")

        if update_fields:
            try:
                profile.save(update_fields=update_fields)
            except IntegrityError:
                return _json_error(
                    "บันทึกไม่สำเร็จ (ข้อมูลชนกันในฐานข้อมูล)",
                    status=409,
                    code="integrity_error",
                )

        if user_update_fields:
            user.save(update_fields=user_update_fields)

    return JsonResponse({"ok": True}, status=200)

