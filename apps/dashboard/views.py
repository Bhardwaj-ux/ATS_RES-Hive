# FILEPATH: apps/dashboard/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.views.generic import TemplateView
from apps.applications.models import Application, CandidateStatusHistory
from apps.jobs.models import Job
from apps.resumes.models import ResumeFile
from apps.tasks.models import Task

ACTIVITY_VERB_MAP = {
    "hired": "hired",
    "rejected": "rejected",
    "shortlisted": "shortlisted",
    "interview": "moved to interview",
    "under_review": "marked under review",
}


def build_recent_activity():
    rows = (
        CandidateStatusHistory.objects.filter(
            changed_by__isnull=False, new_status__in=ACTIVITY_VERB_MAP.keys()
        )
        .values("changed_by__full_name", "changed_by__email", "new_status")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )
    activity = []
    for row in rows:
        name = row["changed_by__full_name"] or row["changed_by__email"]
        verb = ACTIVITY_VERB_MAP.get(row["new_status"], row["new_status"])
        count = row["total"]
        noun = "candidate" if count == 1 else "candidates"
        activity.append(f"{name} {verb} {count} {noun}")
    return activity


SOURCE_COLOR_PALETTE = [
    "#2F5FE0",
    "#F7565B",
    "#86C325",
    "#674A8E",
    "#F7C438",
]


def build_source_breakdown():
    rows = (
        Application.objects.values("source")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    cleaned = {}
    for row in rows:
        label = (row["source"] or "").strip() or "Unspecified"
        cleaned[label] = cleaned.get(label, 0) + row["total"]

    items = sorted(cleaned.items(), key=lambda x: x[1], reverse=True)
    total_count = sum(count for _, count in items)

    breakdown = []
    stops = []
    start = 0
    for i, (label, count) in enumerate(items):
        pct = round((count / total_count) * 100) if total_count else 0
        color = SOURCE_COLOR_PALETTE[i % len(SOURCE_COLOR_PALETTE)]
        breakdown.append({"label": label, "total": count, "pct": pct, "color": color})
        end = start + pct
        stops.append(f"{color} {start}% {end}%")
        start = end

    gradient = (
        f"conic-gradient({', '.join(stops)})"
        if stops
        else "conic-gradient(#dedee7 0% 100%)"
    )
    return breakdown, total_count, gradient


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["job_count"] = Job.objects.filter(is_active=True).count()
        context["interview_count"] = Application.objects.filter(
            status="interview"
        ).count()
        context["candidates_hired"] = Application.objects.filter(status="hired").count()
        context["open_positions"] = Job.objects.filter(is_active=True).count()
        context["candidate_count"] = Application.objects.count()
        context["shortlisted_count"] = Application.objects.filter(
            status="shortlisted"
        ).count()
        context["status_breakdown"] = (
            Application.objects.values("status")
            .annotate(total=Count("id"))
            .order_by("status")
        )
        context["latest_applications"] = Application.objects.select_related("job")[:10]
        context["tasks"] = Task.objects.filter(owner=self.request.user)
        context["recent_activity"] = build_recent_activity()

        source_breakdown, source_total, source_conic_gradient = build_source_breakdown()
        context["source_breakdown"] = source_breakdown
        context["source_total"] = source_total
        context["source_conic_gradient"] = source_conic_gradient
        return context
