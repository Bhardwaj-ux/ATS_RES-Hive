# FILEPATH: apps/tasks/urls.py
from django.urls import path
from . import views

app_name = "tasks"

urlpatterns = [
    path("create/", views.create_task, name="create"),
    path("<int:pk>/toggle/", views.toggle_task, name="toggle"),
    path("<int:pk>/update/", views.update_task, name="update"),
    path("<int:pk>/delete/", views.delete_task, name="delete"),
]
