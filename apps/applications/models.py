# FILEPATH: apps/applications/models.py
import re
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.jobs.models import Job


class Application(TimeStampedModel):
    class Status(models.TextChoices):
        RAW_RECEIVED = "raw_received", "Raw Received"
        UNDER_REVIEW = "under_review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        INTERVIEW = "interview", "Interview"
        HIRED = "hired", "Hired"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    current_location = models.CharField(max_length=150, blank=True)
    total_experience_years = models.DecimalField(
        max_digits=4, decimal_places=1, default=0
    )
    source = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.RAW_RECEIVED
    )
    summary = models.TextField(blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated skills")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications_created",
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("job", "email")

    def __str__(self):
        return f"{self.full_name} - {self.job.title}"

    def skill_list(self):
        if not self.skills:
            return []

        raw_items = re.split(r"[,\n]+", self.skills)
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

    def match_score(self):
        if not self.job_id:
            return None
        job_skills = {s.lower() for s in self.job.skill_list()}
        if not job_skills:
            return None
        own_skills = {s.lower() for s in self.skill_list()}
        if not own_skills:
            return 0
        overlap = job_skills & own_skills
        return round(len(overlap) / len(job_skills) * 100)


class CandidateStatusHistory(TimeStampedModel):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="status_history"
    )
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, choices=Application.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.application.full_name}: {self.old_status} -> {self.new_status}"
