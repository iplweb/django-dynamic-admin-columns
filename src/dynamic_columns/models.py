"""Models for in-database representation of dynamic admin columns configuration."""

import re

from django.conf import settings
from django.contrib.admin import ModelAdmin as DjangoModelAdmin
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Max, Q
from django.utils.datastructures import OrderedSet
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from dynamic_columns.exceptions import CodeAccessNotAllowed
from dynamic_columns.util import qual, str_to_class


def _check_allowed(cname: str, *, target: str = "settings.py") -> None:
    """Raise :class:`CodeAccessNotAllowed` if *cname* is not whitelisted."""
    for path in getattr(settings, "DYNAMIC_COLUMNS_ALLOWED_IMPORT_PATHS", []):
        if cname.startswith(path):
            return
    raise CodeAccessNotAllowed(
        f"Please add {cname} to your project's {target} if you want to "
        f"use DynamicColumnsMixin for that ModelAdmin class -- "
        f"add it to a list ``DYNAMIC_COLUMNS_ALLOWED_IMPORT_PATHS``."
    )


class ModelAdminManager(models.Manager):
    def db_repr(self, model_admin: DjangoModelAdmin) -> "ModelAdmin":
        """Return the **global** :class:`ModelAdmin` row for *model_admin*.

        Global rows have ``user IS NULL`` and act as the default column
        layout for every user that has not personalised it.
        """
        cname = qual(model_admin.__class__)
        _check_allowed(cname)
        return self.get_or_create(
            user=None,
            class_name=cname,
            model_ref=ContentType.objects.get_for_model(model_admin.model),
        )[0]

    def db_repr_for_user(self, model_admin: DjangoModelAdmin, user) -> "ModelAdmin":
        """Return the :class:`ModelAdmin` row that applies for *user*.

        If *user* has personalised their column layout for this admin a
        row with ``user=user`` is returned; otherwise the global row
        (``user IS NULL``) is returned, falling back to creating it.
        """
        cname = qual(model_admin.__class__)
        _check_allowed(cname)
        ct = ContentType.objects.get_for_model(model_admin.model)

        if user is not None and getattr(user, "is_authenticated", False):
            user_row = self.filter(user=user, class_name=cname, model_ref=ct).first()
            if user_row is not None:
                return user_row

        return self.get_or_create(user=None, class_name=cname, model_ref=ct)[0]

    @transaction.atomic
    def clone_for_user(self, model_admin: DjangoModelAdmin, user) -> "ModelAdmin":
        """Create (or return) a personal copy of the global config for *user*.

        The global row is initialised first if it does not yet exist, so
        the personal copy starts as an exact snapshot of the defaults.
        Subsequent calls return the existing personal row unchanged.
        """
        if user is None or not getattr(user, "is_authenticated", False):
            raise ValueError("clone_for_user requires an authenticated user")

        cname = qual(model_admin.__class__)
        _check_allowed(cname)
        ct = ContentType.objects.get_for_model(model_admin.model)

        global_row = self.enable(model_admin)

        user_row, created = self.get_or_create(
            user=user, class_name=cname, model_ref=ct
        )
        if created:
            for column in global_row.modeladmincolumn_set.all():
                ModelAdminColumn.objects.create(
                    parent=user_row,
                    col_name=column.col_name,
                    enabled=column.enabled,
                    ordering=column.ordering,
                )
        return user_row

    def enable(self, model_admin: DjangoModelAdmin) -> "ModelAdmin":
        """Initialise (or refresh) the **global** column layout for *model_admin*.

        Creates the global ``ModelAdmin`` row, then enumerates the
        ``list_display`` / ``list_display_default`` / ``list_display_allowed``
        sources to populate or reconcile :class:`ModelAdminColumn` rows.
        """
        obj = self.db_repr(model_admin)

        # If there is a ``list_display`` setting on ``model_admin``, treat it
        # as ``list_display_default`` -- unless it was left at Django's
        # default ("__str__",) AND ``list_display_always`` is declared, in
        # which case the default is meaningless noise.
        list_display = getattr(model_admin, "list_display", [])
        if list_display == DjangoModelAdmin.list_display:
            if getattr(model_admin, "list_display_always", []):
                list_display = []

        column_sources = [
            (list_display, True),
            (getattr(model_admin, "list_display_default", []), True),
            (getattr(model_admin, "list_display_allowed", []), False),
        ]

        forbidden_columns_patterns = getattr(
            model_admin, "list_display_forbidden", []
        ) + getattr(settings, "DYNAMIC_COLUMNS_FORBIDDEN_COLUMN_NAMES", [])

        list_display_always = getattr(model_admin, "list_display_always", [])

        def column_allowed(field_name):
            if field_name in list_display_always:
                return False
            for elem in forbidden_columns_patterns:
                if re.match(elem, field_name):
                    return False
            return True

        all_columns = set()

        db_max = ModelAdminColumn.objects.filter(parent=obj).aggregate(
            max_cnt=Max("ordering")
        )
        cnt = (db_max["max_cnt"] or 0) + 1

        for column_source, default_value in column_sources:
            if column_source == "__all__":
                columns = [
                    field.name
                    for field in model_admin.model._meta.fields
                    if column_allowed(field.name)
                ]
            else:
                columns = column_source

            for column in [col for col in columns if column_allowed(col)]:
                all_columns.add(column)
                cnt += 1
                obj.modeladmincolumn_set.get_or_create(
                    col_name=column,
                    defaults={"ordering": cnt, "enabled": default_value},
                )

        # Remove stale columns from the **global** row only. Personal rows
        # are user-managed; they are reconciled lazily when the user next
        # saves through the picker.
        obj.modeladmincolumn_set.exclude(col_name__in=all_columns).delete()

        return obj


class ModelAdmin(models.Model):
    """In-database representation of a Django ``ModelAdmin``.

    Rows with ``user IS NULL`` are **global defaults**; rows with a
    populated ``user`` foreign key are that user's **personal copy** of
    the defaults. The picker writes to personal copies, falling back to
    the global row for everyone else.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        help_text=_(
            "If set, this is a personal column configuration owned by "
            "that user. NULL rows are global defaults."
        ),
    )

    class_name = models.TextField()

    model_ref = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    objects = ModelAdminManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["class_name", "model_ref"],
                condition=Q(user__isnull=True),
                name="dyncol_unique_global_modeladmin",
            ),
            models.UniqueConstraint(
                fields=["user", "class_name", "model_ref"],
                condition=Q(user__isnull=False),
                name="dyncol_unique_user_modeladmin",
            ),
        ]
        ordering = ("class_name", "user_id")
        verbose_name = _("Model admin")
        verbose_name_plural = _("Model admins")

    def __str__(self):
        if self.user_id:
            return f"{self.class_name} [{self.user}]"
        return self.class_name

    @cached_property
    def class_ref(self):
        """Resolve ``class_name`` back to its Python class, gated by settings."""
        _check_allowed(self.class_name, target="settings.py")
        return str_to_class(self.class_name)

    def get_list_display(self, model_admin, request):
        """Return ordered, enabled column names for use as ``list_display``.

        ``list_display_always`` from the code-side ``ModelAdmin`` is
        prepended unconditionally; the rest comes from this row's
        :class:`ModelAdminColumn` set.
        """
        ret = OrderedSet()

        always = getattr(model_admin, "list_display_always", [])
        for col in always:
            ret.add(col)

        enabled_cols = self.modeladmincolumn_set.filter(enabled=True).order_by(
            "ordering"
        )
        for col_name in enabled_cols.values_list("col_name", flat=True):
            ret.add(col_name)

        return ret


class ModelAdminColumn(models.Model):
    """A single user-configurable column row of a :class:`ModelAdmin`.

    Stores whether the column is currently visible and its position in
    the changelist relative to its peers.
    """

    parent = models.ForeignKey(
        ModelAdmin, on_delete=models.CASCADE, verbose_name=_("Parent")
    )

    col_name = models.CharField(max_length=255, verbose_name=_("Column name"))

    enabled = models.BooleanField(default=True, verbose_name=_("Enabled"))
    ordering = models.PositiveSmallIntegerField(verbose_name=_("Ordering"))

    class Meta:
        unique_together = [("parent", "col_name")]
        ordering = ("parent", "ordering")
        verbose_name = _("Model admin column")
        verbose_name_plural = _("Model admin columns")

    def __str__(self):
        ret = _("Column") + f' "{self.col_name}"'

        if self.parent_id:
            ret += _(" of model ") + f'"{self.parent.class_name}"'

        return ret
