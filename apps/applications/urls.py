# FILEPATH: apps/applications/urls.py
from django.urls import path
from .views import (
    CandidateCreateView,
    CandidateDeleteView,
    CandidateDetailView,
    CandidateListView,
    CandidateUpdateView,
    bulk_candidate_action,
    candidates_search_ajax,
    quick_status_update,
)

app_name = "applications"

urlpatterns = [
    path("", CandidateListView.as_view(), name="list"),
    path("search/", candidates_search_ajax, name="search-ajax"),
    path("create/", CandidateCreateView.as_view(), name="create"),
    path("bulk-action/", bulk_candidate_action, name="bulk-action"),
    path("<int:pk>/", CandidateDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", CandidateUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", CandidateDeleteView.as_view(), name="delete"),
    path("<int:pk>/status/<str:new_status>/", quick_status_update, name="quick-status"),
]
