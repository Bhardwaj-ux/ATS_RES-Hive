# FILEPATH: apps/tasks/models.py
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel


class Task(TimeStampedModel):
    class Priority(models.TextChoices):
        NONE = "none", "None"
        LOW = "low", "Low"
        MODERATE = "moderate", "Moderate"
        HIGH = "high", "High"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=255)
    is_done = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NONE
    )

    class Meta:
        ordering = ["is_done", "-created_at"]

    def __str__(self):
        return self.title
