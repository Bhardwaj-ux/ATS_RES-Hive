# FILEPATH: apps/jobs/models.py
import re
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel, SoftDeleteModel


class Job(TimeStampedModel, SoftDeleteModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        INTERN = "intern", "Intern"
        CONTRACT = "contract", "Contract"

    class JobStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        ON_HOLD = "on_hold", "Archived"

    title = models.CharField(max_length=255)
    department = models.CharField(max_length=100)
    location = models.CharField(max_length=150, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    experience_min_years = models.PositiveIntegerField(default=0)
    experience_max_years = models.PositiveIntegerField(default=0)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    required_skills = models.TextField(blank=True, help_text="Comma-separated skills")
    status = models.CharField(
        max_length=20, choices=JobStatus.choices, default=JobStatus.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs_created",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def skill_list(self):
        import re

        if not self.required_skills:
            return []
        raw_items = re.split(r"[,\n]+", self.required_skills)
        cleaned = []
        seen = set()
        for item in raw_items:
            skill = item.strip()
            if not skill:
                continue
            key = skill.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(skill)
        return cleaned
