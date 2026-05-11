from builtins import callable

from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from django.contrib.admin import ModelAdmin as DjangoModelAdmin
from django.contrib.admin.utils import NotRelationField, get_model_from_relation
from django.core.exceptions import FieldDoesNotExist
from django.utils.translation import gettext_lazy as _

from dynamic_admin_columns.models import ModelAdmin, ModelAdminColumn


@admin.action(description=_("Enable selected columns"))
def make_enabled(modeladmin, request, queryset):
    queryset.update(enabled=True)


@admin.action(description=_("Disable selected columns"))
def make_disabled(modeladmin, request, queryset):
    queryset.update(enabled=False)


@admin.register(ModelAdmin)
class ModelAdminAdmin(DjangoModelAdmin):
    list_display = ["class_name", "model_ref", "user"]
    list_filter = [("user", admin.EmptyFieldListFilter), "model_ref"]
    search_fields = ["class_name", "user__username"]
    readonly_fields = ["class_name", "model_ref"]


@admin.register(ModelAdminColumn)
class ModelAdminColumnAdmin(SortableAdminMixin, DjangoModelAdmin):
    ordering = ["ordering"]
    list_filter = ["parent", "enabled"]
    list_display = ["col_parent_name", "col_verbose_name", "enabled", "ordering"]
    readonly_fields = ["parent", "col_name", "ordering"]
    actions = [make_disabled, make_enabled]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def col_parent_name(self, obj: ModelAdminColumn):
        """Verbose name of model in column's ModelAdmin."""
        class_ = obj.parent.model_ref.model_class()
        return class_._meta.verbose_name

    col_parent_name.short_description = _("Model admin name")

    def col_verbose_name(self, obj: ModelAdminColumn):
        """Resolve a human-readable name of a ``ModelAdminColumn``.

        Tries, in order:

        1. The model field's ``verbose_name``.
        2. For relation fields, the related model's ``verbose_name``.
        3. The ``short_description`` of a ``ModelAdmin`` callable.
        4. The raw column name as a fallback.
        """
        model = obj.parent.model_ref.model_class()

        try:
            field = model._meta.get_field(obj.col_name)
        except FieldDoesNotExist:
            model_admin_callable = None
            try:
                model_admin_callable = getattr(obj.parent.class_ref, obj.col_name)
            except AttributeError:
                return obj.col_name

            if model_admin_callable and callable(model_admin_callable):
                try:
                    return model_admin_callable.short_description
                except AttributeError:
                    return obj.col_name

        ret = obj.col_name

        if (
            hasattr(field, "verbose_name")
            and field.verbose_name
            and field.verbose_name != obj.col_name
        ):
            ret = field.verbose_name
        else:
            other_model = None
            try:
                other_model = get_model_from_relation(field)
            except NotRelationField:
                pass

            if other_model:
                try:
                    ret = other_model._meta.verbose_name
                except AttributeError:
                    pass

        return ret

    col_verbose_name.short_description = _("Column name")
