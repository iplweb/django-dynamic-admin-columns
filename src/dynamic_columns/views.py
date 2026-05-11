"""AJAX endpoints powering the in-changelist column picker UI."""

import json

from django.contrib.contenttypes.models import ContentType
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.views.decorators.http import require_POST

from dynamic_columns.exceptions import CodeAccessNotAllowed
from dynamic_columns.models import ModelAdmin, ModelAdminColumn
from dynamic_columns.util import qual


def _resolve_admin(model_admin):
    """Return (cname, content_type) for the admin instance."""
    cname = qual(model_admin.__class__)
    ct = ContentType.objects.get_for_model(model_admin.model)
    return cname, ct


@require_POST
def save_columns(request, *, model_admin):
    """Persist the current user's column layout for *model_admin*.

    Expects a JSON body shaped as::

        {"columns": [
            {"col_name": "title", "enabled": true,  "ordering": 1},
            {"col_name": "isbn",  "enabled": false, "ordering": 2},
        ]}

    The picker only manages columns the user is allowed to toggle —
    columns declared in ``list_display_always`` are pinned in code and
    are silently rejected here.
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponseForbidden("Staff access required.")

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload.")

    columns = payload.get("columns")
    if not isinstance(columns, list):
        return HttpResponseBadRequest("Missing 'columns' list.")

    try:
        user_row = ModelAdmin.objects.clone_for_user(model_admin, request.user)
    except CodeAccessNotAllowed as exc:
        return HttpResponseForbidden(str(exc))

    pinned = set(getattr(model_admin, "list_display_always", []))
    valid_names = set(user_row.modeladmincolumn_set.values_list("col_name", flat=True))

    seen = set()
    for index, entry in enumerate(columns, start=1):
        if not isinstance(entry, dict):
            return HttpResponseBadRequest("Each column must be an object.")
        col_name = entry.get("col_name")
        if not isinstance(col_name, str) or col_name not in valid_names:
            continue
        if col_name in pinned or col_name in seen:
            continue
        seen.add(col_name)

        enabled = bool(entry.get("enabled", False))
        try:
            ordering = int(entry.get("ordering", index))
        except (TypeError, ValueError):
            ordering = index

        ModelAdminColumn.objects.filter(parent=user_row, col_name=col_name).update(
            enabled=enabled, ordering=ordering
        )

    return JsonResponse({"ok": True, "user_id": request.user.pk})


@require_POST
def reset_columns(request, *, model_admin):
    """Discard the current user's personal layout and fall back to defaults."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponseForbidden("Staff access required.")

    cname, ct = _resolve_admin(model_admin)
    deleted, _ = ModelAdmin.objects.filter(
        user=request.user, class_name=cname, model_ref=ct
    ).delete()
    if deleted == 0:
        raise Http404("No personal layout to reset.")
    return JsonResponse({"ok": True})
