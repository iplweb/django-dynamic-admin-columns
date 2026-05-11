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

from dynamic_admin_columns.exceptions import CodeAccessNotAllowed
from dynamic_admin_columns.models import ModelAdmin, ModelAdminColumn
from dynamic_admin_columns.util import qual


def _resolve_admin(model_admin):
    """Return (cname, content_type) for the admin instance."""
    cname = qual(model_admin.__class__)
    ct = ContentType.objects.get_for_model(model_admin.model)
    return cname, ct


def _target_row(model_admin, request, scope):
    """Return the :class:`ModelAdmin` row that *scope* targets.

    * ``scope="personal"`` — the current user's personal row, cloned
      lazily from the global defaults on first save.
    * ``scope="global"`` — the global ``user IS NULL`` row. Only
      superusers may target it.
    """
    if scope == "global":
        if not request.user.is_superuser:
            return None, HttpResponseForbidden(
                "Editing global defaults requires superuser permissions."
            )
        return ModelAdmin.objects.enable(model_admin), None

    user_row = ModelAdmin.objects.clone_for_user(model_admin, request.user)
    return user_row, None


@require_POST
def save_columns(request, *, model_admin):
    """Persist the column layout for *model_admin*.

    The JSON body looks like::

        {
            "scope": "personal",        # or "global" (superuser only)
            "columns": [
                {"col_name": "title", "enabled": true,  "ordering": 1},
                {"col_name": "isbn",  "enabled": false, "ordering": 2},
            ]
        }

    Personal saves create or update the requesting user's own row.
    Global saves require ``is_superuser`` and update the
    ``user IS NULL`` row that everyone without a personal layout sees.
    Columns declared in ``list_display_always`` are pinned in code and
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

    scope = payload.get("scope", "personal")
    if scope not in ("personal", "global"):
        return HttpResponseBadRequest("Invalid 'scope'.")

    try:
        target_row, forbidden = _target_row(model_admin, request, scope)
    except CodeAccessNotAllowed as exc:
        return HttpResponseForbidden(str(exc))
    if forbidden is not None:
        return forbidden

    pinned = set(getattr(model_admin, "list_display_always", []))
    valid_names = set(
        target_row.modeladmincolumn_set.values_list("col_name", flat=True)
    )

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

        ModelAdminColumn.objects.filter(parent=target_row, col_name=col_name).update(
            enabled=enabled, ordering=ordering
        )

    return JsonResponse({"ok": True, "scope": scope, "user_id": request.user.pk})


@require_POST
def reset_columns(request, *, model_admin):
    """Discard a column layout and fall back to the next level up.

    * ``scope="personal"`` (default) — deletes the current user's
      personal row. The user reverts to whatever ``user IS NULL`` (the
      global defaults) holds at that moment.
    * ``scope="global"`` — superuser only. Deletes the global row;
      next visit to the admin re-creates it from
      ``list_display_default`` / ``list_display_allowed`` in code.
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponseForbidden("Staff access required.")

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = {}
    scope = payload.get("scope", "personal")
    if scope not in ("personal", "global"):
        return HttpResponseBadRequest("Invalid 'scope'.")

    cname, ct = _resolve_admin(model_admin)

    if scope == "global":
        if not request.user.is_superuser:
            return HttpResponseForbidden(
                "Resetting global defaults requires superuser permissions."
            )
        deleted, _ = ModelAdmin.objects.filter(
            user__isnull=True, class_name=cname, model_ref=ct
        ).delete()
    else:
        deleted, _ = ModelAdmin.objects.filter(
            user=request.user, class_name=cname, model_ref=ct
        ).delete()

    if deleted == 0:
        raise Http404("Nothing to reset for this scope.")
    return JsonResponse({"ok": True, "scope": scope})
