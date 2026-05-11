# django-dynamic-columns — example project

A minimal Django 5 project demonstrating user-controllable admin columns
through `django-dynamic-columns`.

The project ships a single app, `library`, with a `Book` model whose admin
uses `DynamicColumnsMixin`. Run it, create a superuser, log in and inspect
the *Books* admin: you can hide, show and reorder columns at runtime from
the *Model admin columns* admin section.

## Running

From the repository root:

```bash
uv pip install -e ".[dev]"
cd example
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open <http://127.0.0.1:8000/admin/> and log in.

## What to try

1. Open *Library → Books* (the changelist is empty). Add a couple of books.
2. Open *Dynamic columns → Model admin columns*. You will see the rows that
   correspond to the columns declared in `library/admin.py`:
   `author`, `isbn`, `pages` and `notes`.
3. Enable a disabled column (e.g. `pages`) or disable an enabled one and
   reload the books changelist — the column set updates.
4. Drag rows to reorder columns; the books changelist reflects the new
   ordering on the next load.

## Project layout

```
example/
├── manage.py
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
    └── migrations/
        ├── __init__.py
        └── 0001_initial.py
```
