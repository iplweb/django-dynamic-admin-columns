# django-dynamic-admin-columns — grappelli example

Companion to [`example/`](../example), but using
[django-grappelli](https://django-grappelli.readthedocs.io/) as the
admin front-end and a **Polish-localised** UI. Same `BookAdmin`, same
`DynamicColumnsMixin`, same per-user column layouts — proves the
picker works unchanged under a third-party admin skin and renders its
strings through Django's translation machinery.

## Running

There are two paths.

### Plain Django (SQLite, no extras)

```bash
uv pip install -e ".[example-grappelli]"
cd example_grappelli
python manage.py migrate
python manage.py loaddata sample
python manage.py compilemessages -l pl    # compiles library/locale/pl/*.po
python manage.py runserver
```

> `compilemessages` needs GNU gettext (`msgfmt`) on `PATH`
> (`brew install gettext` on macOS).

### Via `run_site` (Postgres + Redis testcontainers, recommended)

The `[example-grappelli]` optional-dependency group pulls in
[`django-grappelli`](https://django-grappelli.readthedocs.io/),
[`django-run-site`](https://github.com/iplweb/django-run-site) and
[`django-dev-helpers`](https://pypi.org/project/django-dev-helpers/).
The combination spins up Postgres + Redis containers on random free
ports, runs migrations, seeds an `admin` / `admin` superuser, and
opens your browser:

```bash
uv pip install -e ".[example-grappelli]"
cd example_grappelli
uv run --no-sync python manage.py compilemessages -l pl
uv run --no-sync python manage.py run_site
```

Stop with `Ctrl-C`; containers and state files are cleaned up
automatically.

## Pre-loaded users

The `sample` fixture creates two Polish-named staff users so you can
demo the per-user feature on the plain-Django path (the `run_site`
path defaults to `admin` / `admin` and also reloads the fixture if you
re-run `loaddata sample`):

| Username | Password    | Rola      |
| -------- | ----------- | --------- |
| `alice`  | `alicepass` | superuser |
| `bob`    | `bobpass`   | superuser |

Open <http://127.0.0.1:8000/admin/> and log in as Alice (or `admin`
under `run_site`).

## What's different from `example/`

| Aspect              | `example/`        | `example_grappelli/`             |
| ------------------- | ----------------- | -------------------------------- |
| Admin front-end     | stock Django      | django-grappelli                 |
| `LANGUAGE_CODE`     | `en-us`           | `pl`                             |
| Timezone            | `UTC`             | `Europe/Warsaw`                  |
| Model strings       | bare English      | wrapped in `gettext_lazy`        |
| Locale catalog      | none              | `library/locale/pl/`             |
| Books in fixture    | English classics  | polskie klasyki literackie       |

The picker (modal, buttons, status messages) is translated via the
catalog already shipped inside `dynamic_admin_columns/locale/pl/`, so
under `LANGUAGE_CODE = "pl"` you see strings such as *"Konfiguruj
kolumny"* and *"Zapisz"* without any extra work.

## What to try

1. **Pinned column** — *Tytuł* is declared in `list_display_always`
   and is always rendered first; it does not appear in the picker.

2. **Default vs allowed** — *Autor* and *ISBN* are visible out of the
   box (`list_display_default`); *Liczba stron*, *Notatki*, *Data
   wydania* and *Język* are hidden but discoverable
   (`list_display_allowed`).

3. **Open the picker** — click the **Kolumny** button in the top-right
   of the *Książki* changelist (grappelli renders it as a pill-style
   object-tool). Drag rows to reorder, toggle checkboxes, then
   **Zapisz**.

4. **Verify it's per-user** — log out, log in as Bob, open the same
   changelist. Bob still sees the original defaults: Alice's tweaks
   did not leak.

5. **Reset** — once a personal layout exists, the picker shows a
   *Porzuć osobisty układ* button. Clicking it deletes the personal
   row and falls back to the global defaults again.

6. **Superuser-only "Global defaults" scope** — log in as a superuser
   (Alice, Bob, or `admin` under `run_site`). The picker modal grows
   a radio switch between *Mój osobisty układ* and *Domyślne globalne*.
   Save in the latter to rewrite the row everyone without a personal
   layout sees.

7. **Inspect the data** — open *Kolumny modułu redagowania* in the
   admin (the `dynamic_admin_columns` app). You'll see one global row
   (`User` empty) and as many personal rows as users have customised
   the admin.

## Compiling the catalog after changes

If you edit `library/locale/pl/LC_MESSAGES/django.po`, recompile:

```bash
cd example_grappelli
python manage.py compilemessages -l pl
```

## Project layout

```
example_grappelli/
├── manage.py
├── runsite.toml
├── example_grappelli_project/
│   ├── __init__.py
│   ├── settings.py        # grappelli first in INSTALLED_APPS; LANGUAGE_CODE=pl
│   ├── urls.py            # /grappelli/ before /admin/
│   ├── asgi.py
│   └── wsgi.py
└── library/
    ├── __init__.py
    ├── apps.py            # verbose_name = _("Library")
    ├── admin.py           # BookAdmin(DynamicColumnsMixin, admin.ModelAdmin)
    ├── models.py          # gettext_lazy on every field
    ├── fixtures/sample.json
    ├── locale/pl/LC_MESSAGES/
    │   ├── django.po
    │   └── django.mo
    └── migrations/
        ├── __init__.py
        └── 0001_initial.py
```
