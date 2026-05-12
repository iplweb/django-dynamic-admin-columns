"""``DynamicColumnsMixin`` — drop-in mixin for Django ``ModelAdmin`` classes."""

from functools import cache, cached_property

from django.apps import apps
from django.urls import path

from dynamic_admin_columns import views
from dynamic_admin_columns.models import ModelAdmin
from dynamic_admin_columns.util import qual


@cache
def _grappelli_installed():
    """Return ``True`` if ``grappelli`` is an installed app.

    Cached because the app registry does not change at runtime; reading it
    on every changelist request would be wasteful.
    """
    return apps.is_installed("grappelli")


class DynamicColumnsMixin:
    """Make a ``ModelAdmin``'s column layout user-configurable at runtime.

    The mixin adds three declarative attributes that complement Django's
    own ``list_display``:

    * ``list_display_always`` — columns that are *always* visible. They
      are not stored in the database and cannot be moved or toggled by
      end-users. Use this for primary identifiers.
    * ``list_display_default`` — columns visible out of the box. The
      user can hide them or change their position.
    * ``list_display_allowed`` — columns hidden by default but
      discoverable from the picker. Useful for power-user fields.
    * ``list_display_forbidden`` — list of regular expressions; matching
      column names are silently dropped (per-admin denylist).

    Visible columns also feed a smarter ``get_list_select_related``:
    when ``list_select_related`` is a *dict* keyed by column name the
    JOINs follow column visibility, so a hidden column doesn't pay its
    join cost.

    The mixin also injects a "Columns" object-tool into the changelist
    that opens a modal picker where the logged-in user can toggle and
    reorder columns. Personal layouts are stored per-user; users
    without a personal layout see the global defaults.
    """

    #: Template used under the stock Django admin. Subclasses that want a
    #: bespoke template should usually override this; under ``grappelli``
    #: ``_change_list_template_grappelli`` is consulted instead. See
    #: ``change_list_template`` below.
    _change_list_template_default = "dynamic_admin_columns/change_list.html"

    #: Template used when ``grappelli`` is in ``INSTALLED_APPS``. Mirrors
    #: the default one but uses grappelli's own button / pill markup so
    #: the picker integrates with grappelli's visual language.
    _change_list_template_grappelli = "dynamic_admin_columns/grappelli/change_list.html"

    @property
    def change_list_template(self):
        """Pick the changelist template based on the installed admin skin.

        Routed through a property so the choice is deferred until request
        time — the Django app registry must be populated before
        ``apps.is_installed`` can be queried reliably. Override either of
        the underscore-prefixed attributes (or the property itself) to
        customise the picker template in a subclass.

        The property is also settable: assigning to
        ``self.change_list_template`` (as e.g. ``django-import-export``'s
        ``ImportExportMixinBase.__init__`` does to compose its own
        changelist template with whatever the host class already chose)
        stores the value on the instance, and subsequent reads return
        that override instead of the skin-derived default. Delete the
        instance attribute to fall back to the dynamic choice again.
        """
        try:
            return self.__dict__["_change_list_template_override"]
        except KeyError:
            pass
        if _grappelli_installed():
            return self._change_list_template_grappelli
        return self._change_list_template_default

    @change_list_template.setter
    def change_list_template(self, value):
        self.__dict__["_change_list_template_override"] = value

    @change_list_template.deleter
    def change_list_template(self):
        self.__dict__.pop("_change_list_template_override", None)

    @cached_property
    def _modeladmin_enabled(self):
        return ModelAdmin.objects.enable(self)

    def get_urls(self):
        urls = super().get_urls()
        opts = self.model._meta
        prefix = f"{opts.app_label}_{opts.model_name}"
        extra = [
            path(
                "dynamic-columns/save/",
                self.admin_site.admin_view(self._dyncol_save_view),
                name=f"{prefix}_dyncol_save",
            ),
            path(
                "dynamic-columns/reset/",
                self.admin_site.admin_view(self._dyncol_reset_view),
                name=f"{prefix}_dyncol_reset",
            ),
        ]
        return extra + urls

    def _dyncol_save_view(self, request):
        return views.save_columns(request, model_admin=self)

    def _dyncol_reset_view(self, request):
        return views.reset_columns(request, model_admin=self)

    def _dyncol_effective_row(self, request):
        # Initialise the global row (no-op after first call) so its
        # columns are always available as the fallback.
        global_row = self._modeladmin_enabled  # noqa: F841

        user = getattr(request, "user", None) if request is not None else None
        return ModelAdmin.objects.db_repr_for_user(self, user)

    def get_list_display(self, request):
        effective = self._dyncol_effective_row(request)
        return effective.get_list_display(model_admin=self, request=request)

    def get_list_select_related(self, request):
        """Honour ``list_select_related = {col_name: [related_field, ...]}``.

        Each key is matched against the *currently visible* columns; the
        special key ``"__always__"`` is unconditional. Lists, tuples and
        sets pass through unchanged for compatibility with vanilla
        Django.
        """
        if isinstance(self.list_select_related, bool):
            return self.list_select_related

        if isinstance(self.list_select_related, list | tuple | set):
            return self.list_select_related

        columns = self.get_list_display(request)

        ret = set()
        for elem in self.list_select_related:
            if elem in columns or elem == "__always__":
                values = self.list_select_related[elem]
                if isinstance(values, str):
                    ret.add(values)
                elif isinstance(values, list | set | tuple):
                    for value in values:
                        ret.add(value)
                else:
                    raise NotImplementedError(
                        f"Handling of values of type {type(values)} not implemented"
                    )
        return ret

    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse
        from django.utils.translation import gettext as _

        effective = self._dyncol_effective_row(request)
        global_row = self._modeladmin_enabled

        pinned = set(getattr(self, "list_display_always", []))

        def rows_for(row):
            return [
                {
                    "col_name": col.col_name,
                    "verbose_name": self._dyncol_verbose_name(col.col_name),
                    "enabled": col.enabled,
                    "ordering": col.ordering,
                }
                for col in row.modeladmincolumn_set.exclude(
                    col_name__in=pinned
                ).order_by("ordering")
            ]

        opts = self.model._meta
        prefix = f"admin:{opts.app_label}_{opts.model_name}"

        has_personal = (
            effective.user_id is not None and effective.user_id == request.user.pk
        )

        # JavaScript-only strings (rendered by ``column-picker.js`` when
        # the user flips the scope radio). The admin's ``jsi18n`` URL
        # only ships ``django.conf``'s catalog, so we cannot rely on
        # ``window.gettext`` to find these — we resolve them on the
        # server here and the template embeds the dict via
        # ``json_script`` for the JS to read out of the DOM.
        js_i18n = {
            "editing_global": _(
                "Editing the global defaults. Every user without a "
                "personal layout will see these columns."
            ),
            "personal_active": _(
                "★ You are viewing your personal layout. Saves apply "
                "only to your account."
            ),
            "global_defaults_status": _(
                "You are viewing the global defaults. Saving will "
                "create a personal layout for your account."
            ),
            "discard_personal": _("Discard personal layout"),
            "reset_global": _("Reset global defaults from code"),
            "confirm_reset_global": _(
                "Reset the GLOBAL defaults? They will be re-derived from "
                "code on the next changelist load."
            ),
            "confirm_discard_personal": _(
                "Discard your personal column layout and use the defaults?"
            ),
            "save_failed": _("Failed to save columns: "),
            "reset_failed": _("Failed to reset."),
        }

        ctx = extra_context or {}
        ctx["dynamic_admin_columns"] = {
            "class_name": qual(self.__class__),
            # Always provide both column sets — JS swaps between them
            # based on the radio. Non-superusers only ever see "personal".
            "personal_columns": rows_for(effective),
            "global_columns": rows_for(global_row),
            "save_url": reverse(f"{prefix}_dyncol_save"),
            "reset_url": reverse(f"{prefix}_dyncol_reset"),
            "has_personal_layout": has_personal,
            "is_superuser": bool(request.user.is_superuser),
            "js_i18n": js_i18n,
        }
        return super().changelist_view(request, extra_context=ctx)

    def _dyncol_verbose_name(self, col_name):
        """Resolve a human-readable label for *col_name* in the picker."""
        from django.core.exceptions import FieldDoesNotExist

        try:
            field = self.model._meta.get_field(col_name)
        except FieldDoesNotExist:
            callable_ = getattr(self, col_name, None)
            if callable_ is not None and callable(callable_):
                return getattr(callable_, "short_description", col_name)
            return col_name

        verbose = getattr(field, "verbose_name", None)
        if verbose and verbose != col_name:
            return verbose
        return col_name
