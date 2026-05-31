"""Initial migration for ``dynamic_admin_columns``.

The schema is built through the schema editor (``create_model``) rather
than a plain ``CreateModel`` operation, guarded so it only runs when the
tables are absent. Two scenarios share this single migration:

* **Fresh install** -- the ``dynamic_columns_*`` tables do not exist, so
  the guard creates them. The ``user`` foreign key is materialised by
  the schema editor against ``settings.AUTH_USER_MODEL``, so it resolves
  to whatever user table the project uses (``auth_user`` by default,
  ``bpp_bppuser`` under a swapped user model, ...). Nothing is
  hard-coded.
* **Pre-existing schema** -- downstream projects that predate the
  package extraction (notably BPP, whose in-tree ``dynamic_columns`` app
  created these tables years ago) already carry them. The guard detects
  the tables and no-ops, so re-applying the migration never collides.

The model side of the migration lives in ``state_operations`` (a
``CreateModel`` pair plus the constraints), keeping Django's migration
state identical to a conventional ``CreateModel`` migration. The
database side is the guarded builder below.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

_MODELS = ("ModelAdmin", "ModelAdminColumn")


def _tables(schema_editor):
    return schema_editor.connection.introspection.table_names()


def create_schema_if_absent(apps, schema_editor):
    """Create the two tables via the schema editor unless they exist.

    Uses the historical models so the ``user`` FK resolves through
    ``settings.AUTH_USER_MODEL`` -- swappable-safe by construction, with
    no literal user-table name baked into the SQL.
    """
    model_admin = apps.get_model("dynamic_admin_columns", "ModelAdmin")
    if model_admin._meta.db_table in _tables(schema_editor):
        return  # legacy / baseline-loaded DB already carries the tables
    for model_name in _MODELS:
        schema_editor.create_model(
            apps.get_model("dynamic_admin_columns", model_name)
        )


def drop_schema_if_present(apps, schema_editor):
    """Reverse of :func:`create_schema_if_absent`."""
    model_admin = apps.get_model("dynamic_admin_columns", "ModelAdmin")
    if model_admin._meta.db_table not in _tables(schema_editor):
        return
    for model_name in reversed(_MODELS):
        schema_editor.delete_model(
            apps.get_model("dynamic_admin_columns", model_name)
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # State only: declare the models (and their constraints) in
        # Django's migration state without emitting any DDL. The
        # database side is handled by the guarded RunPython below, which
        # then sees these models in the accumulated migration state.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="ModelAdmin",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("class_name", models.TextField()),
                        (
                            "model_ref",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="contenttypes.contenttype",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                blank=True,
                                help_text=(
                                    "If set, this is a personal column "
                                    "configuration owned by that user. NULL "
                                    "rows are global defaults."
                                ),
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="User",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Model admin",
                        "verbose_name_plural": "Model admins",
                        "db_table": "dynamic_columns_modeladmin",
                        "ordering": ("class_name", "user_id"),
                    },
                ),
                migrations.CreateModel(
                    name="ModelAdminColumn",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "col_name",
                            models.CharField(
                                max_length=255, verbose_name="Column name"
                            ),
                        ),
                        (
                            "enabled",
                            models.BooleanField(default=True, verbose_name="Enabled"),
                        ),
                        (
                            "ordering",
                            models.PositiveSmallIntegerField(verbose_name="Ordering"),
                        ),
                        (
                            "parent",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="dynamic_admin_columns.modeladmin",
                                verbose_name="Parent",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Model admin column",
                        "verbose_name_plural": "Model admin columns",
                        "db_table": "dynamic_columns_modeladmincolumn",
                        "ordering": ("parent", "ordering"),
                    },
                ),
                migrations.AddConstraint(
                    model_name="modeladmin",
                    constraint=models.UniqueConstraint(
                        condition=models.Q(("user__isnull", True)),
                        fields=("class_name", "model_ref"),
                        name="dyncol_unique_global_modeladmin",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="modeladmin",
                    constraint=models.UniqueConstraint(
                        condition=models.Q(("user__isnull", False)),
                        fields=("user", "class_name", "model_ref"),
                        name="dyncol_unique_user_modeladmin",
                    ),
                ),
                migrations.AlterUniqueTogether(
                    name="modeladmincolumn",
                    unique_together={("parent", "col_name")},
                ),
            ],
            database_operations=[],
        ),
        migrations.RunPython(
            create_schema_if_absent,
            reverse_code=drop_schema_if_present,
        ),
    ]
