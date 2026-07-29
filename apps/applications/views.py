# FILEPATH: apps/applications/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from apps.jobs.models import Job
from .forms import ApplicationForm
from .models import Application
from .services import record_status_change


class CandidateListView(LoginRequiredMixin, ListView):
    model = Application
    template_name = "candidates/list.html"
    context_object_name = "applications"

    def get_queryset(self):
        qs = Application.objects.select_related("job").all()
        q = self.request.GET.get("q", "").strip()
        job_id = self.request.GET.get("job")
        status = self.request.GET.get("status")
        source = self.request.GET.get("source", "").strip()
        exp_min = self.request.GET.get("exp_min")
        exp_max = self.request.GET.get("exp_max")

        if q:
            qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q))
        if job_id:
            qs = qs.filter(job_id=job_id)
        if status:
            qs = qs.filter(status=status)
        if source:
            qs = qs.filter(source__icontains=source)
        if exp_min:
            try:
                qs = qs.filter(total_experience_years__gte=float(exp_min))
            except ValueError:
                pass
        if exp_max:
            try:
                qs = qs.filter(total_experience_years__lte=float(exp_max))
            except ValueError:
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for application in context["applications"]:
            score = application.match_score()
            if score is None:
                application.score_level = "na"
                application.score_display = "—"
            else:
                application.score_display = score
                if score >= 70:
                    application.score_level = "green"
                elif score >= 40:
                    application.score_level = "yellow"
                else:
                    application.score_level = "red"
        context["jobs_for_filter"] = Job.objects.filter(is_active=True).order_by(
            "title"
        )
        context["status_choices"] = Application.Status.choices
        context["current_filters"] = self.request.GET
        return context


class CandidateCreateView(LoginRequiredMixin, CreateView):
    model = Application
    form_class = ApplicationForm
    template_name = "candidates/form.html"
    success_url = reverse_lazy("applications:list")

    def dispatch(self, request, *args, **kwargs):
        if not Job.objects.filter(is_active=True).exists():
            messages.warning(request, "Create a job first before adding candidates.")
            return redirect("jobs:create")
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["job"].queryset = Job.objects.filter(is_active=True).order_by(
            "title"
        )
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        record_status_change(
            self.object,
            self.request.user,
            "",
            self.object.status,
            "Initial application status",
        )
        return response


class CandidateDetailView(LoginRequiredMixin, DetailView):
    model = Application
    template_name = "candidates/detail.html"
    context_object_name = "application"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status == Application.Status.RAW_RECEIVED:
            old_status = self.object.status
            self.object.status = Application.Status.UNDER_REVIEW
            self.object.save(update_fields=["status", "updated_at"])
            record_status_change(
                self.object,
                request.user,
                old_status,
                self.object.status,
                "Auto-updated on first view",
            )
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class CandidateUpdateView(LoginRequiredMixin, UpdateView):
    model = Application
    form_class = ApplicationForm
    template_name = "candidates/form.html"
    success_url = reverse_lazy("applications:list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["job"].queryset = Job.objects.filter(is_active=True).order_by(
            "title"
        )
        return form

    def form_valid(self, form):
        old_status = self.get_object().status
        response = super().form_valid(form)
        record_status_change(
            self.object,
            self.request.user,
            old_status,
            self.object.status,
            "Application updated",
        )
        return response


class CandidateDeleteView(LoginRequiredMixin, DeleteView):
    model = Application
    template_name = "candidates/confirm_delete.html"
    success_url = reverse_lazy("applications:list")
    context_object_name = "application"


@login_required
def quick_status_update(request, pk, new_status):
    application = get_object_or_404(Application, pk=pk)
    old_status = application.status
    application.status = new_status
    application.save(update_fields=["status", "updated_at"])
    record_status_change(
        application, request.user, old_status, new_status, "Quick action"
    )
    messages.success(request, "Candidate status updated successfully.")
    return redirect("applications:detail", pk=pk)


@login_required
@require_POST
def bulk_candidate_action(request):
    action = request.POST.get("action")
    ids = request.POST.getlist("ids[]")
    if not ids:
        return JsonResponse(
            {"ok": False, "error": "No candidates selected."}, status=400
        )

    queryset = Application.objects.filter(pk__in=ids)

    if action == "delete":
        count = queryset.count()
        queryset.delete()
        return JsonResponse({"ok": True, "message": f"{count} candidate(s) deleted."})

    status_map = {
        "reject": Application.Status.REJECTED,
        "shortlist": Application.Status.SHORTLISTED,
        "under_review": Application.Status.UNDER_REVIEW,
        "interview": Application.Status.INTERVIEW,
        "hired": Application.Status.HIRED,
    }
    if action not in status_map:
        return JsonResponse({"ok": False, "error": "Unknown action."}, status=400)

    new_status = status_map[action]
    updated = 0
    for application in queryset:
        old_status = application.status
        if old_status != new_status:
            application.status = new_status
            application.save(update_fields=["status", "updated_at"])
            record_status_change(
                application, request.user, old_status, new_status, "Bulk action"
            )
            updated += 1

    return JsonResponse({"ok": True, "message": f"{updated} candidate(s) updated."})
