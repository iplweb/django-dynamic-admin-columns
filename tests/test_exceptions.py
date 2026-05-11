import pytest

from dynamic_admin_columns.exceptions import CodeAccessNotAllowed


def test_code_access_not_allowed_is_raisable():
    with pytest.raises(CodeAccessNotAllowed, match="boom"):
        raise CodeAccessNotAllowed("boom")
