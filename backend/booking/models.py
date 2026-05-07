from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


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
    profile_image = models.FileField(upload_to="profiles/%Y/%m/", blank=True, null=True)

    @property
    def is_mkt(self) -> bool:
        return self.role == self.Role.MKT

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อแบรนด์")
    logo_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="โลโก้แบรนด์ (URL)")
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")

    class Meta:
        verbose_name = "แบรนด์"
        verbose_name_plural = "แบรนด์ทั้งหมด"

    def __str__(self):
        return self.name

# ==========================================
# 2. ตาราง Channel
# ==========================================
class Channel(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="ชื่อช่องทาง (เช่น TikTok)")
    code = models.CharField(max_length=10, unique=True, verbose_name="ตัวย่อ (เช่น TT)")
    icon_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="ไอคอนช่องทาง (URL)")
    color_hex = models.CharField(max_length=7, default='#3788d8', verbose_name="สีประจำช่องทาง (HEX)") 
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")

    class Meta:
        verbose_name = "ช่องทาง Live"
        verbose_name_plural = "ช่องทาง Live ทั้งหมด"

    def __str__(self):
        return f"{self.name} ({self.code})"

# ==========================================
# 3. ตาราง Profile (เพิ่มช่องรองรับ LINE Login)
# ==========================================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=(
        ('admin', 'Admin'),
        ('mkt', 'Marketing'),
        ('brand', 'Brand'),
        ('user', 'User'),
    ), default='user')
    
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name="สังกัดแบรนด์")
    
    #  ฟิลด์สำหรับเก็บรหัส LINE (ใช้ทำ LINE Login และส่งแจ้งเตือนผ่าน LINE OA ได้)
    line_uid = models.CharField(max_length=255, unique=True, blank=True, null=True, verbose_name="LINE User ID (UID)")
    
    kof = models.CharField(max_length=50, blank=True, null=True, verbose_name="KOF")
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bank_account_number = models.CharField(max_length=30, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    
    # เมื่อล็อกอินผ่าน LINE เราสามารถดึงรูปโปรไฟล์จาก LINE มาเก็บที่ฟิลด์นี้ได้เลยอัตโนมัติ
    photo_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="รูปโปรไฟล์ (URL)")
    
    is_verified = models.BooleanField(default=False, verbose_name="ตรวจสอบตัวตนแล้ว")

    def __str__(self):
        return f"Profile of {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# ==========================================
# 4. ตาราง LiveSchedule
# ==========================================
class LiveSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_schedules', verbose_name="ผู้ไลฟ์")
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_schedules', verbose_name="ผู้แก้ไขล่าสุด")
    mkts = models.ManyToManyField(User, blank=True, related_name='managed_schedules', verbose_name="MKT ผู้ดูแล")
    
    title = models.CharField(max_length=200, verbose_name="หัวข้อ Live")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='live_schedules', verbose_name="แบรนด์")
    channel = models.ForeignKey(Channel, on_delete=models.SET_NULL, null=True, blank=True, related_name='live_schedules', verbose_name="ช่องทาง Live")
    
    total_raw = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="ยอดขายที่ User กรอก")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="ยอดขายจริง")
    view_count = models.PositiveIntegerField(default=0, verbose_name="จำนวนผู้เข้าชม")
    
    is_verified = models.BooleanField(default=False, verbose_name="ตรวจสอบถูกต้อง (T/F)")
    is_cancelled = models.BooleanField(default=False, verbose_name="ยกเลิกรายการ (Y/N)")
    note = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ")
    
    start_time = models.DateTimeField(verbose_name="เวลาเริ่ม")
    end_time = models.DateTimeField(verbose_name="เวลาจบ")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ตาราง Live"
        verbose_name_plural = "ตาราง Live ทั้งหมด"

    def __str__(self):
        if self.is_cancelled:
            status = "❌ [CANCELLED]"
        elif self.is_verified:
            status = "✅ [VERIFIED]"
        else:
            status = "⏳ [PENDING]"
        
        brand_name = self.brand.name if self.brand else "N/A"
        channel_code = self.channel.code if self.channel else "N/A"
        return f"{status} [{brand_name} | {channel_code}] {self.title}"

# ==========================================
# 5. ตาราง LiveScheduleImage
# ==========================================
class LiveScheduleImage(models.Model):
    live_schedule = models.ForeignKey(LiveSchedule, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(max_length=500)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)