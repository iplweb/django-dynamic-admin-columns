"""Tests for ``dynamic_columns.util``."""

import pytest

from dynamic_columns.util import qual, str_to_class


def test_qual_returns_full_import_path():
    from django.contrib.admin import ModelAdmin as DjangoModelAdmin

    assert qual(DjangoModelAdmin) == "django.contrib.admin.options.ModelAdmin"


def test_qual_with_local_class():
    from dynamic_columns.models import ModelAdmin

    assert qual(ModelAdmin) == "dynamic_columns.models.ModelAdmin"


def test_str_to_class_returns_class_object():
    from django.contrib.admin import ModelAdmin as DjangoModelAdmin

    assert str_to_class("django.contrib.admin.options.ModelAdmin") is DjangoModelAdmin


def test_str_to_class_raises_on_missing_attribute():
    with pytest.raises(NameError, match="doesn't exist"):
        str_to_class("django.contrib.admin.options.NotARealClass")
