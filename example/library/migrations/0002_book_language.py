from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0001_initial"),
    ]

    operations = [
        # No-op: 0001_initial already declares the ``language`` column.
        # This migration exists only to allow the project to evolve the
        # initial schema in subsequent revisions without rewriting it.
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
