from __future__ import annotations

from ..models import User


def redirect_url_for_user(user: User) -> str:
    """
    Return the first page a verified user should see after login.
    Product roles live on Profile; Django superusers still go to backoffice.
    """
    profile = getattr(user, "profile", None)
    profile_role = getattr(profile, "role", "user")

    if user.is_superuser or profile_role == "admin":
        return "/backoffice/dashboard"
    if profile_role == "brand":
        return "/brand/dashboard"
    return "/dashboard"


def is_backoffice_admin(user: User) -> bool:
    """
    Backoffice is reserved for product admins only.
    Accept Django superusers or Profile.role=admin.
    """
    if not getattr(user, "is_authenticated", False):
        return False

    profile = getattr(user, "profile", None)
    profile_role = getattr(profile, "role", "user")
    return bool(user.is_superuser or profile_role == "admin")
