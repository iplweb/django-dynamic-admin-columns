"""The initial migration must tolerate a pre-existing schema.

Downstream projects that predate the package extraction re-apply
``0001_initial`` onto a database that already carries the
``dynamic_columns_*`` tables. The canonical example is BPP, whose
in-tree ``dynamic_columns`` app created those tables years before the
code was split out into this package. A plain ``CreateModel`` collides
with the existing tables; the migration must detect them and no-op,
while still building the schema from scratch on a fresh install.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

APP = "dynamic_admin_columns"
TABLES = ("dynamic_columns_modeladmin", "dynamic_columns_modeladmincolumn")


@pytest.mark.django_db(transaction=True)
def test_initial_migration_is_idempotent_against_preexisting_tables():
    # Roll the app back to an empty schema, then recreate the tables by
    # hand -- this stands in for a legacy / baseline-loaded database that
    # already holds them before the migration is applied.
    MigrationExecutor(connection).migrate([(APP, None)])

    executor = MigrationExecutor(connection)
    state = executor.loader.project_state((APP, "0001_initial"))
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(state.apps.get_model(APP, "ModelAdmin"))
        schema_editor.create_model(state.apps.get_model(APP, "ModelAdminColumn"))

    # Re-applying the initial migration onto the existing tables must not
    # raise "table already exists".
    MigrationExecutor(connection).migrate([(APP, "0001_initial")])

    existing = connection.introspection.table_names()
    for table in TABLES:
        assert table in existing
