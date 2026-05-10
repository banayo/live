from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    Brand,
    Channel,
    LiveSchedule,
    LiveScheduleImage,
    Profile,
    User,
)


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    fk_name = "user"
    can_delete = False

    readonly_fields = ("line_uid",)

    fields = (
        "role",
        "brand",
        "profile_image",
        "line_uid",
        "photo_url",
        "kof",
        "phone_number",
        "bank_name",
        "bank_account_number",
        "is_verified",
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_active", "is_superuser")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("ข้อมูลส่วนตัว"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("สิทธิ์ของ Django"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("วันที่สำคัญ"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2", "email"),
            },
        ),
    )

    inlines = (ProfileInline,)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    ordering = ("user__username",)
    list_display = ("user", "role", "phone_number", "line_uid", "is_verified", "brand")
    list_filter = ("is_verified", "role")
    search_fields = ("user__username", "user__email", "phone_number", "line_uid", "kof")
    autocomplete_fields = ("user", "brand")
    list_editable = ("is_verified",)


class LiveScheduleImageInline(admin.TabularInline):
    model = LiveScheduleImage
    extra = 0


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(LiveSchedule)
class LiveScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "brand",
        "channel",
        "start_time",
        "is_verified",
        "is_cancelled",
    )
    list_filter = ("is_verified", "is_cancelled", "brand", "channel")
    search_fields = ("title", "user__username", "note")
    autocomplete_fields = ("user", "edited_by", "brand", "channel")
    date_hierarchy = "start_time"
    inlines = (LiveScheduleImageInline,)


@admin.register(LiveScheduleImage)
class LiveScheduleImageAdmin(admin.ModelAdmin):
    ordering = ("live_schedule", "order", "pk")
    list_display = ("live_schedule", "order", "created_at")
    list_editable = ("order",)
