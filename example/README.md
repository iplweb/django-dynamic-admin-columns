# django-dynamic-admin-columns — example project

A minimal Django 5 project demonstrating user-controllable admin
columns through `django-dynamic-admin-columns`. Run it, log in as either of
two pre-baked users and watch how each user keeps their **own** column
layout for the same `BookAdmin`.

## Running

There are two paths.

### Plain Django (SQLite, no extras)

```bash
uv pip install -e ".[dev]"
cd example
python manage.py migrate
python manage.py loaddata sample
python manage.py runserver
```

### Via `run_site` (Postgres + Redis testcontainers, recommended)

`example/requirements-dev.txt` pins
[`django-run-site`](https://github.com/iplweb/django-run-site) (from a
GitHub tag — not yet on PyPI under that name) and
[`django-dev-helpers`](https://pypi.org/project/django-dev-helpers/).
The combination spins up Postgres + Redis containers on random free
ports, runs migrations, seeds an `admin` / `admin` superuser, and
opens your browser:

```bash
uv pip install -e .
uv pip install -r example/requirements-dev.txt
cd example
uv run --no-sync python manage.py run_site
```

This is the same dev orchestrator we use in real production
projects. `runsite.toml` at the project root configures it
(database name, superuser, banner). The state files
(`.run_site_token`, `.run_site_port`, `.run_site_pg_port`,
`.run_site_redis_port`) appear next to `manage.py` for the lifetime
of the process so LLM coding agents and integration scripts can pick
them up.

Stop with `Ctrl-C`; containers and state files are cleaned up
automatically.

## Pre-loaded users

`sample` creates two staff users so you can demo the per-user feature
on the plain-Django path (the `run_site` path defaults to
`admin` / `admin`, but the fixture also gets loaded for that flow if
you re-run `loaddata sample`):

| Username | Password    | Role       |
| -------- | ----------- | ---------- |
| `alice`  | `alicepass` | superuser  |
| `bob`    | `bobpass`   | superuser  |

Open <http://127.0.0.1:8000/admin/> and log in as Alice (or `admin`
under `run_site`).

## What to try

1. **Pinned column** — the *Title* column is declared in
   `list_display_always` and is always rendered first. It does not
   appear in the picker because the user cannot move or hide it.

2. **Default vs allowed** — *Author* and *ISBN* are visible out of the
   box (`list_display_default`); *Pages*, *Notes*, *Published on* and
   *Language* are hidden but discoverable (`list_display_allowed`).

3. **Open the picker** — click the **Columns** button in the top right
   of the *Books* changelist. Drag rows to reorder, toggle checkboxes,
   then **Save**.

4. **Verify it's per-user** — log out, log in as Bob, open the same
   *Books* changelist. Bob still sees the original defaults: Alice's
   tweaks did not leak.

5. **Reset** — once a personal layout exists, the picker shows a
   *Discard personal layout* button. Clicking it deletes the personal
   row and falls back to the global defaults again.

6. **Superuser-only "Global defaults" scope** — log in as a superuser
   (Alice, Bob, or `admin` under `run_site`). The picker modal grows
   a radio switch between *My personal layout* and *Global defaults*.
   Save in the latter to rewrite the row everyone without a personal
   layout sees.

7. **Inspect the data** — open *Dynamic admin columns → Model admins*
   in the admin. You'll see one global row (`User` empty) and as many
   personal rows as users have customised the admin.

## Project layout

```
example/
├── manage.py
├── runsite.toml             # run-site / dev-helpers configuration
├── example_project/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── library/
    ├── __init__.py
    ├── apps.py
    ├── admin.py
    ├── models.py
    ├── fixtures/
    │   └── sample.json
    └── migrations/
        ├── __init__.py
        └── 0001_initial.py
```
