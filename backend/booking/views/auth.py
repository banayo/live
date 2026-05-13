from __future__ import annotations

import json
from typing import Any

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..models import User
from ..services.profile_avatar import resolve_profile_avatar_url
from ..services.registration import create_pending_user
from ..services.roles import is_backoffice_admin, redirect_url_for_user


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
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


@require_GET
def auth_me(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=200)

    profile = getattr(request.user, "profile", None)
    profile_role = getattr(profile, "role", None)
    return JsonResponse(
        {
            "authenticated": True,
            "user": {
                "id": request.user.id,
                "username": request.user.get_username(),
                "role": profile_role,
            },
            "profile": {
                "is_verified": bool(getattr(profile, "is_verified", False)),
                "line_uid": getattr(profile, "line_uid", None),
                "role": profile_role,
                "photo_url": str(getattr(profile, "photo_url", "") or "").strip()
                if profile
                else "",
                "avatar_url": resolve_profile_avatar_url(request, profile),
            },
        }
    )


@require_GET
def backoffice_auth_check(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not is_backoffice_admin(request.user):
        return HttpResponse(status=403)
    return HttpResponse(status=204)


@csrf_exempt
@require_POST
def auth_register(request: HttpRequest) -> JsonResponse:
    name = str(request.POST.get("name") or "").strip()
    phone_number = str(request.POST.get("phone_number") or "").strip()
    email = str(request.POST.get("email") or "").strip().lower()
    image = request.FILES.get("profile_image")

    password = str(request.POST.get("password") or "")
    password_confirm = str(request.POST.get("password_confirm") or "")

    if not name or not phone_number or not email:
        return _json_error("Missing required registration fields.", status=400, code="missing_fields")

    if not password:
        return _json_error("Password is required.", status=400, code="missing_password")

    if password != password_confirm:
        return _json_error("Passwords do not match.", status=400, code="password_mismatch")

    try:
        validate_password(password, user=User(email=email, username="pending"))
    except DjangoValidationError as exc:
        msg = " ".join(exc.messages) if exc.messages else "รหัสผ่านไม่ผ่านเกณฑ์ความปลอดภัย"
        return _json_error(msg, status=400, code="weak_password")

    if User.objects.filter(email__iexact=email).exists():
        return _json_error("Email already registered.", status=409, code="email_exists")

    if image:
        content_type = str(getattr(image, "content_type", "") or "")
        if not content_type.startswith("image/"):
            return _json_error("Profile image must be an image file.", status=400, code="invalid_image")
        if image.size > 5 * 1024 * 1024:
            return _json_error("Profile image is too large.", status=400, code="image_too_large")

    user = create_pending_user(
        name=name,
        email=email,
        phone_number=phone_number,
        profile_image=image,
        password=password,
    )

    return JsonResponse(
        {
            "ok": True,
            "message": "Registration submitted. Please wait for admin verification.",
            "user_id": user.id,
        },
        status=201,
    )


@csrf_exempt
@require_POST
def auth_login(request: HttpRequest) -> JsonResponse:
    data = _get_request_json(request)
    if data is None:
        return _json_error("Invalid JSON body.", status=400, code="invalid_json")

    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    remember = bool(data.get("remember", True))

    if not username or not password:
        return _json_error("Missing credentials.", status=400, code="missing_credentials")

    user = authenticate(request, username=username, password=password)
    if not user:
        return _json_error("Invalid credentials.", status=401, code="invalid_credentials")

    profile = getattr(user, "profile", None)
    if profile is not None and not bool(getattr(profile, "is_verified", False)):
        return _json_error("Account pending verification.", status=403, code="not_verified")

    login(request, user)
    if not remember:
        request.session.set_expiry(0)

    return JsonResponse({"ok": True, "redirect_url": redirect_url_for_user(user)})


@csrf_exempt
@require_POST
def auth_logout(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({"ok": True})
