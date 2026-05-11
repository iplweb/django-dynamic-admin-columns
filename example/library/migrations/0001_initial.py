from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Book",
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
                ("title", models.CharField(max_length=255, verbose_name="Title")),
                ("author", models.CharField(max_length=255, verbose_name="Author")),
                (
                    "isbn",
                    models.CharField(
                        blank=True, default="", max_length=13, verbose_name="ISBN"
                    ),
                ),
                (
                    "pages",
                    models.PositiveIntegerField(default=0, verbose_name="Pages"),
                ),
                (
                    "notes",
                    models.TextField(blank=True, default="", verbose_name="Notes"),
                ),
                (
                    "published_on",
                    models.DateField(
                        blank=True, null=True, verbose_name="Published on"
                    ),
                ),
            ],
            options={
                "verbose_name": "Book",
                "verbose_name_plural": "Books",
                "ordering": ("title",),
            },
        ),
    ]
