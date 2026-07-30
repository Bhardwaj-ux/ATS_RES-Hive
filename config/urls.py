from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="dashboard:index", permanent=False)),
    path("account/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("jobs/", include("apps.jobs.urls")),
    path("jdimport/", include("apps.jdimport.urls")),
    path("candidates/", include("apps.applications.urls")),
    path("resumes/", include("apps.resumes.urls")),
    path("folks/", include("apps.folks.urls")),
    path("interviews/", include("apps.interviews.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("api/auth/", include("apps.accounts.api_urls")),
    path("api/jobs/", include("apps.jobs.api_urls")),
    path("api/applications/", include("apps.applications.api_urls")),
    path("app/", TemplateView.as_view(template_name="react_index.html"), name="react-app"),
    re_path(r"^app/.*$", TemplateView.as_view(template_name="react_index.html")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
