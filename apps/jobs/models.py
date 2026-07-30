# FILEPATH: apps/jobs/models.py
import re
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel, SoftDeleteModel


class Job(TimeStampedModel, SoftDeleteModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        INTERN = "intern", "Internship"
        CONTRACT = "contract", "Contract"

    class JobStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        ON_HOLD = "on_hold", "Archived"

    class Priority(models.TextChoices):
        P0 = "P0", "P0 — Critical (Hire Immediately)"
        P1 = "P1", "P1 — High priority"
        P2 = "P2", "P2 — Moderate priority"
        P3 = "P3", "P3 — Low priority (Backlog)"

    class Department(models.TextChoices):
        SALES = "Sales", "Sales"
        ODM = "ODM", "ODM"
        BOX_BUILD = "Box Build", "Box Build"
        HR = "Human Resources", "Human Resources"
        XOR = "XOR", "XOR"
        MARKETING = "Marketing", "Marketing"
        FINANCE = "Finance", "Finance"
        IT_ADMIN = "IT & Admin", "IT & Admin"

    class CTCMode(models.TextChoices):
        RANGE = "range", "Range"
        NEGOTIABLE = "negotiable", "Negotiable"
        HIDDEN = "hidden", "Do not mention"

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
    skills_data = models.JSONField(default=list, blank=True)
    priority = models.CharField(
        max_length=2, choices=Priority.choices, default=Priority.P2
    )
    ctc_mode = models.CharField(
        max_length=20, choices=CTCMode.choices, default=CTCMode.HIDDEN
    )
    ctc_min = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ctc_max = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
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

    def sync_skills_data_from_text(self):
        """Fallback: build skills_data from required_skills if skills_data is empty."""
        if self.skills_data:
            return
        raw_items = re.split(r"[,\n]+", self.required_skills or "")
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
            cleaned.append({"name": skill, "priority": False})
        self.skills_data = cleaned

    def skill_list(self):
        """Backward-compatible flat list of skill names, starred first."""
        self.sync_skills_data_from_text()
        starred = [s["name"] for s in self.skills_data if s.get("priority")]
        unstarred = [s["name"] for s in self.skills_data if not s.get("priority")]
        return starred + unstarred

    def skill_pills(self):
        """List of dicts for template rendering with star state, starred first."""
        self.sync_skills_data_from_text()
        starred = [s for s in self.skills_data if s.get("priority")]
        unstarred = [s for s in self.skills_data if not s.get("priority")]
        return starred + unstarred

    def ctc_display(self):
        if self.ctc_mode == self.CTCMode.NEGOTIABLE:
            return "Negotiable"
        if self.ctc_mode == self.CTCMode.HIDDEN:
            return "Not disclosed"
        if self.ctc_min is not None and self.ctc_max is not None:
            return f"{self.ctc_min:g} – {self.ctc_max:g} LPA"
        return "Not disclosed"
