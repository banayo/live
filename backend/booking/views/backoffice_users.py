from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..models import Brand, Profile, User
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


def _avatar_url(request: HttpRequest, profile: Profile | None) -> str:
    """Prefer uploaded file; otherwise external LINE avatar URL."""
    if profile is None:
        return ""
    try:
        if getattr(profile.profile_image, "name", ""):
            return request.build_absolute_uri(profile.profile_image.url)
    except Exception:
        pass
    u = str(getattr(profile, "photo_url", "") or "").strip()
    return u


@require_GET
def backoffice_users_list(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Unauthorized"}, status=401)
    if not is_backoffice_admin(request.user):
        return JsonResponse({"ok": False, "message": "Forbidden"}, status=403)

    brands = list(
        Brand.objects.order_by("name").values("id", "name", "is_active")
    )

    qs = (
        User.objects.select_related("profile", "profile__brand")
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
            "profile__brand__id",
            "profile__brand__name",
        )
    )

    users: list[dict[str, Any]] = []
    for u in qs:
        profile = getattr(u, "profile", None)
        brand = getattr(profile, "brand", None) if profile else None
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
                "avatar_url": _avatar_url(request, profile),
                "role": getattr(profile, "role", "user") or "user",
                "is_verified": bool(getattr(profile, "is_verified", False)),
                "line_connected": bool(line_uid_raw),
                "brand": {"id": brand.id, "name": brand.name} if brand else None,
                "created_at": u.date_joined.isoformat() if u.date_joined else None,
            }
        )

    return JsonResponse({"ok": True, "users": users, "brands": brands}, status=200)


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
    is_verified_raw = data.get("is_verified", None)
    if isinstance(is_verified_raw, str) and is_multipart:
        is_verified_raw = is_verified_raw.strip().lower()
        if is_verified_raw in {"true", "1", "yes", "on"}:
            is_verified_raw = True
        elif is_verified_raw in {"false", "0", "no", "off", ""}:
            is_verified_raw = False
    is_verified = is_verified_raw

    brand_id_raw = data.get("brand_id", None)
    if isinstance(brand_id_raw, str) and is_multipart:
        brand_id_raw = brand_id_raw.strip()
        if brand_id_raw == "":
            brand_id_raw = ""
        else:
            try:
                brand_id_raw = int(brand_id_raw)
            except Exception:
                return _json_error("Invalid brand_id.", status=400, code="invalid_brand_id")
    brand_id = brand_id_raw
    phone_number = data.get("phone_number", None)
    kof = data.get("kof", None)
    bank_account_number = data.get("bank_account_number", None)
    bank_name = data.get("bank_name", None)
    photo_url = data.get("photo_url", None)
    line_uid = data.get("line_uid", None)
    profile_image_file = request.FILES.get("profile_image") if is_multipart else None

    allowed_roles = {"admin", "brand", "user"}
    if role is not None and role not in allowed_roles:
        return _json_error("Invalid role.", status=400, code="invalid_role")

    if is_verified is not None and not isinstance(is_verified, bool):
        return _json_error("Invalid is_verified.", status=400, code="invalid_verified")

    if brand_id is not None and brand_id != "" and not isinstance(brand_id, int):
        return _json_error("Invalid brand_id.", status=400, code="invalid_brand_id")

    brand_obj = None
    if isinstance(brand_id, int):
        brand_obj = Brand.objects.filter(pk=brand_id).first()
        if not brand_obj:
            return _json_error("Brand not found.", status=404, code="brand_not_found")

    if phone_number is not None:
        phone_number = str(phone_number).strip()[:15]
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
            .select_related("profile", "profile__brand")
            .filter(pk=user_id)
            .first()
        )
        if not user:
            return _json_error("User not found.", status=404, code="user_not_found")

        profile = Profile.objects.select_for_update().get(user=user)

        if role is not None:
            profile.role = role
        if is_verified is not None:
            profile.is_verified = bool(is_verified)
        if brand_id is not None:
            profile.brand = brand_obj
        if phone_number is not None:
            profile.phone_number = phone_number
        if kof is not None:
            profile.kof = kof
        if bank_account_number is not None:
            profile.bank_account_number = bank_account_number
        if bank_name is not None:
            profile.bank_name = bank_name
        if photo_url is not None:
            profile.photo_url = photo_url if photo_url else None
        if line_uid is not None:
            profile.line_uid = line_uid_normalized
        if profile_image_file is not None:
            profile.profile_image = profile_image_file

        update_fields = [
            "role",
            "is_verified",
            "brand",
            "phone_number",
            "kof",
            "bank_account_number",
            "bank_name",
            "photo_url",
            "line_uid",
            "profile_image",
        ]
        profile.save(update_fields=update_fields)

    return JsonResponse({"ok": True}, status=200)

