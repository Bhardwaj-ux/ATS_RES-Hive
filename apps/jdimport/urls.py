# FILEPATH: apps/jdimport/urls.py
from django.urls import path
from . import views

app_name = "jdimport"

urlpatterns = [
    path("upload/", views.upload_page, name="upload"),
    path("batch/start/", views.batch_start, name="batch_start"),
    path("batch/<int:batch_id>/upload/", views.upload_file, name="upload_file"),
    path("file/<int:file_id>/convert/", views.convert_file, name="convert_file"),
    path("file/<int:file_id>/extract/", views.extract_file, name="extract_file"),
    path("review/", views.review_list, name="review_list"),
    path("review/<int:file_id>/", views.review_detail, name="review_detail"),
    path("review/<int:file_id>/reject/", views.reject_file, name="reject_file"),
    path("review/bulk-action/", views.bulk_action, name="bulk_action"),
]
