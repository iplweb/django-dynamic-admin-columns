"""Initial migration for ``dynamic_admin_columns``.

This is a plain Django ``CreateModel`` migration. Fresh installs run
it as-is; downstream projects that come from the pre-extraction
in-tree ``dynamic_columns`` app (notably BPP) are expected to ship a
companion migration that runs *before* this one and ``--fake``-marks
this initial as already applied. See
``bpp.0416_rename_dynamic_columns_to_admin`` in the BPP repository
for the reference implementation.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
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
                            "If set, this is a personal column configuration "
                            "owned by that user. NULL rows are global defaults."
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
                    models.CharField(max_length=255, verbose_name="Column name"),
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
    ]
