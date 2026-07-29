# FILEPATH: apps/jdimport/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.jobs.forms import JobForm
from apps.jobs.models import Job
from .models import JDImportBatch, JDImportFile
from .services.conversion import (
    ConversionError,
    convert_docx_to_markdown,
    convert_pdf_to_markdown,
)
from .services.extraction import ExtractionError, extract_job_fields

MAX_FILES_PER_BATCH = 10


@login_required
def upload_page(request):
    return render(request, "jdimport/upload.html")


@login_required
@require_POST
def batch_start(request):
    batch = JDImportBatch.objects.create(created_by=request.user)
    return JsonResponse({"batch_id": batch.pk})


@login_required
@require_POST
def upload_file(request, batch_id):
    batch = get_object_or_404(JDImportBatch, pk=batch_id)

    if batch.files.count() >= MAX_FILES_PER_BATCH:
        return JsonResponse(
            {
                "error": f"This batch already has the maximum of {MAX_FILES_PER_BATCH} files."
            },
            status=400,
        )

    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"error": "No file received."}, status=400)

    lower_name = uploaded.name.lower()
    if lower_name.endswith(".pdf"):
        file_type = "pdf"
    elif lower_name.endswith(".docx"):
        file_type = "docx"
    else:
        return JsonResponse(
            {"error": "Only PDF and DOCX files are supported."}, status=400
        )

    if uploaded.size > 8 * 1024 * 1024:
        return JsonResponse({"error": "File exceeds the 8 MB limit."}, status=400)

    jd_file = JDImportFile.objects.create(
        batch=batch,
        original_filename=uploaded.name,
        file=uploaded,
        file_type=file_type,
        status=JDImportFile.Status.UPLOADED,
    )
    return JsonResponse({"file_id": jd_file.pk})


@login_required
@require_POST
def convert_file(request, file_id):
    jd_file = get_object_or_404(JDImportFile, pk=file_id)
    jd_file.status = JDImportFile.Status.CONVERTING
    jd_file.save(update_fields=["status", "updated_at"])

    try:
        jd_file.file.open("rb")
        if jd_file.file_type == "pdf":
            markdown_text = convert_pdf_to_markdown(jd_file.file)
        else:
            markdown_text = convert_docx_to_markdown(jd_file.file)
        jd_file.file.close()
    except ConversionError as exc:
        jd_file.status = JDImportFile.Status.FAILED
        jd_file.error_message = str(exc)[:500]
        jd_file.save(update_fields=["status", "error_message", "updated_at"])
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        jd_file.status = JDImportFile.Status.FAILED
        jd_file.error_message = f"Unexpected conversion error: {exc}"[:500]
        jd_file.save(update_fields=["status", "error_message", "updated_at"])
        return JsonResponse({"error": "Unexpected conversion error."}, status=500)

    if not markdown_text.strip():
        jd_file.status = JDImportFile.Status.FAILED
        jd_file.error_message = "No readable text was found in this file."
        jd_file.save(update_fields=["status", "error_message", "updated_at"])
        return JsonResponse({"error": jd_file.error_message}, status=400)

    jd_file.markdown_text = markdown_text
    jd_file.status = JDImportFile.Status.CONVERTED
    jd_file.save(update_fields=["markdown_text", "status", "updated_at"])
    return JsonResponse({"status": "converted"})


@login_required
@require_POST
def extract_file(request, file_id):
    jd_file = get_object_or_404(JDImportFile, pk=file_id)

    if jd_file.status != JDImportFile.Status.CONVERTED:
        return JsonResponse(
            {"error": "This file has not been converted yet."}, status=400
        )

    jd_file.status = JDImportFile.Status.EXTRACTING
    jd_file.save(update_fields=["status", "updated_at"])

    try:
        extracted = extract_job_fields(jd_file.markdown_text)
    except ExtractionError as exc:
        jd_file.status = JDImportFile.Status.FAILED
        jd_file.error_message = str(exc)[:500]
        jd_file.save(update_fields=["status", "error_message", "updated_at"])
        return JsonResponse({"error": str(exc)}, status=400)

    jd_file.extracted_json = extracted
    jd_file.status = JDImportFile.Status.EXTRACTED
    jd_file.save(update_fields=["extracted_json", "status", "updated_at"])
    return JsonResponse({"status": "extracted"})


@login_required
def review_list(request):
    files = (
        JDImportFile.objects.filter(status=JDImportFile.Status.EXTRACTED)
        .select_related("batch")
        .order_by("-created_at")
    )
    return render(request, "jdimport/review_list.html", {"files": files})


@login_required
def review_detail(request, file_id):
    jd_file = get_object_or_404(JDImportFile, pk=file_id)
    extracted = jd_file.extracted_json or {}

    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.created_by = request.user
            job.save()
            jd_file.status = JDImportFile.Status.APPROVED
            jd_file.created_job = job
            jd_file.save(update_fields=["status", "created_job", "updated_at"])
            messages.success(
                request, f'"{job.title}" was created from the imported job description.'
            )
            return redirect("jdimport:review_list")
    else:
        initial = {
            "title": extracted.get("title", ""),
            "department": extracted.get("department", ""),
            "location": extracted.get("location", ""),
            "employment_type": extracted.get("employment_type", "full_time"),
            "experience_min_years": extracted.get("experience_min_years", 0),
            "experience_max_years": extracted.get("experience_max_years", 0),
            "description": extracted.get("description", ""),
            "requirements": extracted.get("requirements", ""),
            "required_skills": ", ".join(extracted.get("skills", [])).lower(),
            "status": Job.JobStatus.DRAFT,
        }
        form = JobForm(initial=initial)

    return render(
        request, "jdimport/review_detail.html", {"jd_file": jd_file, "form": form}
    )


@login_required
@require_POST
def reject_file(request, file_id):
    jd_file = get_object_or_404(
        JDImportFile, pk=file_id, status=JDImportFile.Status.EXTRACTED
    )
    jd_file.status = JDImportFile.Status.REJECTED
    jd_file.save(update_fields=["status", "updated_at"])
    messages.success(request, f'"{jd_file.original_filename}" was rejected.')
    return redirect("jdimport:review_list")


@login_required
@require_POST
def bulk_action(request):
    action = request.POST.get("action")
    file_ids = request.POST.getlist("file_ids")

    if action not in {"approve", "reject"}:
        messages.error(request, "Unknown bulk action.")
        return redirect("jdimport:review_list")

    files = JDImportFile.objects.filter(
        pk__in=file_ids, status=JDImportFile.Status.EXTRACTED
    )

    if action == "reject":
        count = files.update(status=JDImportFile.Status.REJECTED)
        messages.success(request, f"Rejected {count} job description(s).")
        return redirect("jdimport:review_list")

    created = 0
    for jd_file in files:
        extracted = jd_file.extracted_json or {}
        job = Job.objects.create(
            title=extracted.get("title", "") or jd_file.original_filename,
            department=extracted.get("department", ""),
            location=extracted.get("location", ""),
            employment_type=extracted.get("employment_type", "full_time"),
            experience_min_years=extracted.get("experience_min_years", 0),
            experience_max_years=extracted.get("experience_max_years", 0),
            description=extracted.get("description", ""),
            requirements=extracted.get("requirements", ""),
            required_skills=", ".join(extracted.get("skills", [])),
            status=Job.JobStatus.DRAFT,
            created_by=request.user,
        )
        jd_file.status = JDImportFile.Status.APPROVED
        jd_file.created_job = job
        jd_file.save(update_fields=["status", "created_job", "updated_at"])
        created += 1

    messages.success(request, f"Created {created} job role(s).")
    return redirect("jdimport:review_list")
