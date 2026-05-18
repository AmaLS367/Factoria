from pathlib import Path
from typing import Generator
from unittest import mock

import pytest

from backend.utils.templates import (
    BUILTIN_TEMPLATES,
    Template,
    delete_template,
    get_template,
    list_templates,
    save_template,
)


@pytest.fixture
def temp_templates_file(tmp_path: Path) -> Generator[Path, None, None]:
    path = tmp_path / "templates.json"
    with mock.patch("backend.utils.templates._user_templates_path", return_value=str(path)):
        yield path


def test_list_templates_returns_builtins(temp_templates_file: mock.MagicMock) -> None:
    templates = list_templates()
    assert len(templates) >= len(BUILTIN_TEMPLATES)
    builtin_slugs = [t.slug for t in BUILTIN_TEMPLATES]
    for t in templates:
        if t.is_builtin:
            assert t.slug in builtin_slugs


def test_save_and_get_user_template(temp_templates_file: mock.MagicMock) -> None:
    template = Template(
        slug="my-custom-template",
        name="My Custom Template",
        description="A test template",
        item_label="test item",
        column_name="Test ID",
        target_fields=["Field 1", "Field 2"],
    )
    save_template(template)

    t = get_template("my-custom-template")
    assert t is not None
    assert t.slug == "my-custom-template"
    assert t.name == "My Custom Template"
    assert not t.is_builtin
    assert t.target_fields == ["Field 1", "Field 2"]


def test_cannot_overwrite_builtin(temp_templates_file: mock.MagicMock) -> None:
    builtin = BUILTIN_TEMPLATES[0]
    template = Template(
        slug=builtin.slug,
        name="Hacked Template",
        description="Trying to overwrite",
        item_label="hacked",
        column_name="Hacked ID",
        target_fields=["Hacked Field"],
    )

    with pytest.raises(ValueError, match=f"Cannot overwrite built-in template '{builtin.slug}'."):
        save_template(template)


def test_cannot_delete_builtin(temp_templates_file: mock.MagicMock) -> None:
    builtin = BUILTIN_TEMPLATES[0]
    with pytest.raises(ValueError, match=f"Cannot delete built-in template '{builtin.slug}'."):
        delete_template(builtin.slug)


def test_delete_user_template(temp_templates_file: mock.MagicMock) -> None:
    template = Template(
        slug="to-delete",
        name="To Delete",
        description="",
        item_label="item",
        column_name="ID",
        target_fields=[],
    )
    save_template(template)

    assert get_template("to-delete") is not None

    deleted = delete_template("to-delete")
    assert deleted is True

    assert get_template("to-delete") is None

    # Try deleting again
    assert delete_template("to-delete") is False
