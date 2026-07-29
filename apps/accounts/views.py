# FILEPATH: apps/accounts/views.py
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from apps.applications.models import Application
from .forms import (
    AvatarUploadForm,
    EmailAuthenticationForm,
    RegisterForm,
    UserProfileForm,
)
from .models import User, UserPreference


class UserLoginView(LoginView):
    template_name = "auth/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    pass


class RegisterView(CreateView):
    template_name = "auth/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("dashboard:index")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard:index")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        auth_login(
            self.request,
            self.object,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        messages.success(
            self.request, "Welcome to Elecbits ATS! Your account has been created."
        )
        return response


NOTIFICATION_EVENTS = [
    ("new_application", "New candidate application"),
    ("status_change", "Candidate status change"),
    ("job_created", "New job role created"),
    ("resume_uploaded", "Resume uploaded"),
]

TAB_CHOICES = [
    "profile",
    "team",
    "permissions",
    "pipeline",
    "notifications",
    "security",
    "integrations",
    "api",
    "data",
    "audit",
]

COMING_SOON_TABS = {
    "integrations": "Integrations",
    "api": "API & Webhooks",
    "data": "Data Export & Import",
    "audit": "Audit Log",
}


def default_notification_prefs():
    return {
        key: {"email": True, "in_app": True, "push": False}
        for key, _ in NOTIFICATION_EVENTS
    }


@login_required
def settings_view(request):
    tab = request.GET.get("tab", "profile")
    if tab not in TAB_CHOICES:
        tab = "profile"

    prefs, created = UserPreference.objects.get_or_create(user=request.user)
    if created and not prefs.profile_name:
        full_name = request.user.get_full_name().strip()
        prefs.profile_name = full_name or request.user.email
        prefs.save(update_fields=["profile_name"])

    profile_identity_form = None

    if request.method == "POST":
        if request.POST.get("form") == "profile_identity":
            profile_identity_form = UserProfileForm(request.POST, instance=request.user)
            if profile_identity_form.is_valid():
                profile_identity_form.save()
                messages.success(request, "Profile details updated successfully.")
                return redirect(f"{reverse('accounts:settings')}?tab=profile")

        elif request.POST.get("form") == "notifications":
            updated = {}
            for key, _label in NOTIFICATION_EVENTS:
                updated[key] = {
                    "email": request.POST.get(f"{key}_email") == "on",
                    "in_app": request.POST.get(f"{key}_in_app") == "on",
                    "push": request.POST.get(f"{key}_push") == "on",
                }
            prefs.notification_prefs = updated
            prefs.save(update_fields=["notification_prefs"])
            messages.success(request, "Notification preferences updated successfully.")
            return redirect(f"{reverse('accounts:settings')}?tab=notifications")

    if profile_identity_form is None:
        profile_identity_form = UserProfileForm(instance=request.user)

    notification_prefs = prefs.notification_prefs or default_notification_prefs()
    for key, _label in NOTIFICATION_EVENTS:
        notification_prefs.setdefault(
            key, {"email": True, "in_app": True, "push": False}
        )

    team_members = (
        User.objects.all().prefetch_related("role_assignments__role").order_by("email")
    )
    role_assignment_map = {}
    for member in team_members:
        assignment = member.role_assignments.first()
        role_assignment_map[member.pk] = (
            assignment.role.name if assignment else "No role assigned"
        )

    current_role = role_assignment_map.get(request.user.pk, "No role assigned")

    context = {
        "active_tab": tab,
        "coming_soon_tabs": COMING_SOON_TABS,
        "profile_identity_form": profile_identity_form,
        "current_role": current_role,
        "team_members": team_members,
        "role_assignment_map": role_assignment_map,
        "pipeline_stages": Application.Status.choices,
        "notification_events": NOTIFICATION_EVENTS,
        "notification_prefs": notification_prefs,
    }
    return render(request, "accounts/settings.html", context)


@login_required
@require_POST
def upload_avatar(request):
    form = AvatarUploadForm(request.POST, request.FILES, instance=request.user)
    if not form.is_valid():
        error_list = form.errors.get("avatar") or ["Upload failed."]
        return JsonResponse({"ok": False, "error": " ".join(error_list)}, status=400)

    form.save()
    return JsonResponse({"ok": True, "avatar_url": request.user.avatar.url})
