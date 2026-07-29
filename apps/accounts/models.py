# FILEPATH: apps/accounts/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import TimeStampedModel
from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    class Location(models.TextChoices):
        BENGALURU = "bengaluru", "Bengaluru"
        DELHI = "delhi", "Delhi"
        GURUGRAM = "gurugram", "Gurugram"

    job_title = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=20, choices=Location.choices, blank=True)
    linkedin_url = models.URLField(max_length=300, blank=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name or self.email

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email

    def initials(self):
        name = self.get_full_name().strip()
        parts = [p for p in name.split() if p]
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        if parts:
            return parts[0][:2].upper()
        return self.email[:2].upper()


class Role(TimeStampedModel):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class UserRoleAssignment(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.CASCADE,
        related_name="user_assignments",
    )

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.email} -> {self.role.name}"


class UserPreference(models.Model):
    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
        ("system", "System"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    profile_name = models.CharField(max_length=120, blank=True)
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="system")
    sidebar_collapsed = models.BooleanField(default=False)
    compact_tables = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    notification_prefs = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.email}"
