from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from apps.jdimport.models import JDImportFile
from .forms import JobForm
from .models import Job


class JobListView(LoginRequiredMixin, ListView):
    model = Job
    template_name = "jobs/list.html"
    context_object_name = "jobs"

    def get_queryset(self):
        qs = Job.objects.filter(is_active=True)
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        employment_type = self.request.GET.get("employment_type", "").strip()
        location = self.request.GET.get("location", "").strip()

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(department__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if employment_type:
            qs = qs.filter(employment_type=employment_type)
        if location:
            qs = qs.filter(location__icontains=location)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_jd_review_count"] = JDImportFile.objects.filter(
            status=JDImportFile.Status.EXTRACTED
        ).count()
        context["status_choices"] = Job.JobStatus.choices
        context["employment_type_choices"] = Job.EmploymentType.choices
        context["current_filters"] = {
            "q": self.request.GET.get("q", ""),
            "status": self.request.GET.get("status", ""),
            "employment_type": self.request.GET.get("employment_type", ""),
            "location": self.request.GET.get("location", ""),
        }
        return context


class JobCreateView(LoginRequiredMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/form.html"
    success_url = reverse_lazy("jobs:list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class JobDetailView(LoginRequiredMixin, DetailView):
    model = Job
    template_name = "jobs/detail.html"
    context_object_name = "job"


class JobUpdateView(LoginRequiredMixin, UpdateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/form.html"
    success_url = reverse_lazy("jobs:list")


class JobDeleteView(LoginRequiredMixin, DeleteView):
    model = Job
    template_name = "jobs/confirm_delete.html"
    success_url = reverse_lazy("jobs:list")
    context_object_name = "job"


@login_required
@require_POST
def bulk_job_action(request):
    action = request.POST.get("action")
    ids = request.POST.getlist("ids[]")
    if not ids:
        return JsonResponse(
            {"ok": False, "error": "No job roles selected."}, status=400
        )

    queryset = Job.objects.filter(pk__in=ids)

    if action == "delete":
        count = queryset.count()
        queryset.delete()
        return JsonResponse({"ok": True, "message": f"{count} job role(s) deleted."})

    status_map = {
        "open": Job.JobStatus.OPEN,
        "closed": Job.JobStatus.CLOSED,
        "archived": Job.JobStatus.ON_HOLD,
    }
    if action not in status_map:
        return JsonResponse({"ok": False, "error": "Unknown action."}, status=400)

    updated = queryset.update(status=status_map[action])
    return JsonResponse({"ok": True, "message": f"{updated} job role(s) updated."})
