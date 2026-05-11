from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dynamic_columns", "0004_alter_modeladmin_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="modeladmin",
            name="user",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "If set, this is a personal column configuration owned by "
                    "that user. NULL rows are global defaults."
                ),
                null=True,
                on_delete=models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="modeladmin",
            unique_together=set(),
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
    ]
