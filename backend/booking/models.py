from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        HOST = "host", "Host"
        MKT = "mkt", "Marketing"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.HOST,
        db_index=True,
    )

    # Use FileField to avoid requiring Pillow (ImageField dependency).
    # Served via MEDIA_URL (nginx should serve /media/).
    profile_image = models.FileField(
        upload_to="profiles/%Y/%m/",
        blank=True,
        null=True,
    )

    @property
    def is_mkt(self) -> bool:
        return self.role == self.Role.MKT

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser


class LiveSchedule(models.Model):
    host = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="live_schedules",
        db_index=True,
    )

    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    start = models.DateTimeField(db_index=True)
    end = models.DateTimeField(db_index=True)
    all_day = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["host", "start"]),
            models.Index(fields=["start", "end"]),
        ]
        ordering = ["-start"]

    def __str__(self) -> str:
        return f"{self.title} ({self.start:%Y-%m-%d %H:%M})"

