# FILEPATH: apps/tasks/views.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from .models import Task


def _serialize(task):
    return {
        "id": task.pk,
        "title": task.title,
        "is_done": task.is_done,
        "priority": task.priority,
        "priority_label": task.get_priority_display(),
    }


@login_required
@require_POST
def create_task(request):
    title = (request.POST.get("title") or "").strip()
    priority = request.POST.get("priority", Task.Priority.NONE)
    if not title:
        return JsonResponse(
            {"ok": False, "error": "Task title is required."}, status=400
        )
    if priority not in Task.Priority.values:
        priority = Task.Priority.NONE
    task = Task.objects.create(owner=request.user, title=title, priority=priority)
    return JsonResponse({"ok": True, "task": _serialize(task)})


@login_required
@require_POST
def toggle_task(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    task.is_done = not task.is_done
    task.save(update_fields=["is_done", "updated_at"])
    return JsonResponse({"ok": True, "task": _serialize(task)})


@login_required
@require_POST
def update_task(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    title = request.POST.get("title")
    priority = request.POST.get("priority")
    if title is not None and title.strip():
        task.title = title.strip()
    if priority is not None and priority in Task.Priority.values:
        task.priority = priority
    task.save(update_fields=["title", "priority", "updated_at"])
    return JsonResponse({"ok": True, "task": _serialize(task)})


@login_required
@require_POST
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    task.delete()
    return JsonResponse({"ok": True})
