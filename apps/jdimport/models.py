# FILEPATH: apps/jdimport/models.py
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.jobs.models import Job


class JDImportBatch(TimeStampedModel):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jd_import_batches",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CREATED
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch {self.pk} ({self.get_status_display()})"

    @property
    def file_count(self):
        return self.files.count()


def jd_upload_path(instance, filename):
    return f"jd_imports/batch_{instance.batch_id}/{filename}"


class JDImportFile(TimeStampedModel):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        CONVERTING = "converting", "Converting"
        CONVERTED = "converted", "Converted"
        EXTRACTING = "extracting", "Extracting"
        EXTRACTED = "extracted", "Ready for Review"
        FAILED = "failed", "Failed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    batch = models.ForeignKey(
        JDImportBatch, on_delete=models.CASCADE, related_name="files"
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=jd_upload_path)
    file_type = models.CharField(max_length=10, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADED
    )
    markdown_text = models.TextField(blank=True)
    extracted_json = models.JSONField(null=True, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    created_job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="imported_from",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.original_filename
