# django-dynamic-columns — example project

A minimal Django 5 project demonstrating user-controllable admin
columns through `django-dynamic-columns`. Run it, log in as either of
two pre-baked users and watch how each user keeps their **own** column
layout for the same `BookAdmin`.

## Running

From the repository root:

```bash
uv pip install -e ".[dev]"
cd example
python manage.py migrate
python manage.py loaddata sample
python manage.py runserver
```

`sample` creates two staff users so you can demo the per-user feature:

| Username | Password    | Role       |
| -------- | ----------- | ---------- |
| `alice`  | `alicepass` | superuser  |
| `bob`    | `bobpass`   | superuser  |

Open <http://127.0.0.1:8000/admin/> and log in as Alice.

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
   *Reset to defaults* button. Clicking it deletes the personal row
   and falls back to the global defaults again.

6. **Inspect the data** — open *Dynamic columns → Model admins* in the
   admin. You'll see one global row (`User` empty) and as many
   personal rows as users have customised the admin.

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
    ├── fixtures/
    │   └── sample.json
    └── migrations/
        ├── __init__.py
        └── 0001_initial.py
```
