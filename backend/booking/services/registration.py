from __future__ import annotations

import re
import secrets
from typing import Any

from django.db import transaction

from ..models import User


def unique_username(seed: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", seed.strip().lower()).strip("_")
    base = (base or f"user_{secrets.token_hex(4)}")[:24]
    username = base
    suffix = 0
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f"{base}_{suffix}"[:30]
    return username


def create_pending_user(
    *,
    name: str,
    email: str,
    phone_number: str = "",
    profile_image: Any = None,
    username_seed: str = "",
) -> User:
    """
    Create a user that must be verified by admin before access.
    """
    with transaction.atomic():
        user = User.objects.create(
            username=unique_username(username_seed or email.split("@", 1)[0] or phone_number),
            email=email,
            first_name=name[:150],
        )
        user.set_unusable_password()
        user.save()

        profile = user.profile
        if profile_image:
            profile.profile_image = profile_image
        profile.phone_number = phone_number[:15]
        profile.role = "user"
        profile.is_verified = False
        update_fields = ["phone_number", "role", "is_verified"]
        if profile_image:
            update_fields.append("profile_image")
        profile.save(update_fields=update_fields)

    return user
