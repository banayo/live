from __future__ import annotations

import json
import secrets
from urllib.error import HTTPError, URLError

from django.contrib.auth import login
from django.http import HttpRequest
from django.shortcuts import redirect
from django.views.decorators.http import require_GET

from ..models import Profile, User
from ..services.line_oauth import (
    build_authorize_url,
    exchange_code_for_access_token,
    fetch_line_profile,
    line_env,
)
from ..services.roles import redirect_url_for_user


@require_GET
def line_authorize(request: HttpRequest):
    channel_id, _, redirect_uri = line_env()
    if not channel_id or not redirect_uri:
        return redirect("/login?error=line_not_configured")

    state = secrets.token_urlsafe(24)
    request.session["line_oauth_state"] = state

    return redirect(
        build_authorize_url(
            channel_id=channel_id,
            redirect_uri=redirect_uri,
            state=state,
        )
    )


@require_GET
def line_callback(request: HttpRequest):
    """
    LINE Login callback. User access is allowed only after admin verification.
    """
    code = (request.GET.get("code") or "").strip()
    state = (request.GET.get("state") or "").strip()
    error = (request.GET.get("error") or "").strip()

    if error:
        return redirect("/login?error=line_denied")

    expected_state = request.session.get("line_oauth_state")
    if not expected_state or not state or state != expected_state:
        return redirect("/login?error=state_mismatch")

    if not code:
        return redirect("/login?error=missing_code")

    channel_id, channel_secret, redirect_uri = line_env()
    if not channel_id or not channel_secret or not redirect_uri:
        return redirect("/login?error=line_not_configured")

    try:
        access_token = exchange_code_for_access_token(
            code=code,
            channel_id=channel_id,
            channel_secret=channel_secret,
            redirect_uri=redirect_uri,
        )
        if not access_token:
            return redirect("/login?error=token_failed")

        profile_data = fetch_line_profile(access_token)
        line_uid = str(profile_data.get("userId") or "").strip()
        display_name = str(profile_data.get("displayName") or "").strip()
        picture_url = str(profile_data.get("pictureUrl") or "").strip()

        if not line_uid:
            return redirect("/login?error=profile_failed")

    except (HTTPError, URLError, ValueError, json.JSONDecodeError):
        return redirect("/login?error=line_api_error")

    profile = Profile.objects.select_related("user").filter(line_uid=line_uid).first()
    if not profile:
        base_username = f"line_{line_uid[:10]}"
        username = base_username
        suffix = 0
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base_username}_{suffix}"

        user = User.objects.create(username=username, first_name=display_name[:150])
        user.set_unusable_password()
        user.save(update_fields=["password"])

        profile = user.profile
        profile.line_uid = line_uid
        profile.role = "user"
        profile.is_verified = False
        if picture_url:
            profile.photo_url = picture_url
        profile.save()
    else:
        # Keep LINE profile picture URL fresh for avatar fallback (file image still wins in APIs).
        profile_updates: list[str] = []
        if picture_url and (profile.photo_url or "").strip() != picture_url:
            profile.photo_url = picture_url
            profile_updates.append("photo_url")
        if display_name and profile.user.first_name != display_name[:150]:
            User.objects.filter(pk=profile.user_id).update(first_name=display_name[:150])
        if profile_updates:
            profile.save(update_fields=profile_updates)

    if not profile.is_verified:
        return redirect("/login?error=not_verified")

    login(request, profile.user)
    return redirect(redirect_url_for_user(profile.user))
