import json
import os
from dataclasses import dataclass, field
from typing import Optional

from backend.config import settings


@dataclass
class Template:
    slug: str
    name: str
    description: str
    item_label: str
    column_name: str
    target_fields: list[str]
    is_builtin: bool = field(default=False)


BUILTIN_TEMPLATES: list[Template] = [
    Template(
        slug="spare-parts",
        name="Spare Parts",
        description="Technical data for industrial spare parts and components.",
        item_label="spare part",
        column_name="Item ID",
        target_fields=[
            "Name",
            "Description",
            "Weight",
            "Dimensions",
            "Material",
            "Manufacturer",
            "Country of Origin",
        ],
        is_builtin=True,
    ),
    Template(
        slug="suppliers",
        name="Suppliers",
        description="Supplier profiles including contact, products, and certifications.",
        item_label="supplier",
        column_name="Supplier ID",
        target_fields=[
            "Company Name",
            "Website",
            "Contact Email",
            "Products / Services",
            "Country",
            "Certifications",
            "Annual Revenue",
        ],
        is_builtin=True,
    ),
    Template(
        slug="products",
        name="Products",
        description="Product catalogue data: features, pricing, manufacturer.",
        item_label="product",
        column_name="Product ID",
        target_fields=[
            "Product Name",
            "Category",
            "Price Range",
            "Key Features",
            "Target Market",
            "Manufacturer",
            "Warranty",
        ],
        is_builtin=True,
    ),
    Template(
        slug="companies",
        name="Companies",
        description="Company profiles: industry, financials, key info.",
        item_label="company",
        column_name="Company Name",
        target_fields=[
            "Industry",
            "Founded",
            "Headquarters",
            "Revenue",
            "Employees",
            "Key Products / Services",
            "Website",
        ],
        is_builtin=True,
    ),
    Template(
        slug="technical-specs",
        name="Technical Specs",
        description="Electrical / mechanical component specifications.",
        item_label="component",
        column_name="Part Number",
        target_fields=[
            "Voltage Rating",
            "Current Rating",
            "Operating Temperature",
            "Dimensions",
            "Weight",
            "Standards / Certifications",
            "Datasheet URL",
        ],
        is_builtin=True,
    ),
]


def _user_templates_path() -> str:
    return os.path.join(os.path.dirname(settings.db_path), "templates.json")


def _load_user_templates() -> list[Template]:
    path = _user_templates_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            templates = []
            for item in data:
                templates.append(
                    Template(
                        slug=item.get("slug", ""),
                        name=item.get("name", ""),
                        description=item.get("description", ""),
                        item_label=item.get("item_label", ""),
                        column_name=item.get("column_name", ""),
                        target_fields=item.get("target_fields", []),
                        is_builtin=False,
                    )
                )
            return templates
    except (json.JSONDecodeError, IOError):
        return []


def _save_user_templates(templates: list[Template]) -> None:
    path = _user_templates_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([t.__dict__ for t in templates], f, ensure_ascii=False, indent=2)


def list_templates() -> list[Template]:
    """Return built-ins followed by user templates, merged."""
    return BUILTIN_TEMPLATES + _load_user_templates()


def get_template(slug: str) -> Optional[Template]:
    """Return template by slug (built-in or user), None if not found."""
    for t in list_templates():
        if t.slug == slug:
            return t
    return None


def save_template(template: Template) -> None:
    """Save or overwrite a user template. Raises ValueError if slug collides with a built-in."""
    for builtin in BUILTIN_TEMPLATES:
        if builtin.slug == template.slug:
            raise ValueError(f"Cannot overwrite built-in template '{template.slug}'.")

    template.is_builtin = False
    user_templates = _load_user_templates()

    # Overwrite if exists
    for i, t in enumerate(user_templates):
        if t.slug == template.slug:
            user_templates[i] = template
            break
    else:
        user_templates.append(template)

    _save_user_templates(user_templates)


def delete_template(slug: str) -> bool:
    """Delete a user template. Returns False if not found. Raises ValueError if it is a built-in."""
    for builtin in BUILTIN_TEMPLATES:
        if builtin.slug == slug:
            raise ValueError(f"Cannot delete built-in template '{slug}'.")

    user_templates = _load_user_templates()
    new_templates = [t for t in user_templates if t.slug != slug]

    if len(new_templates) == len(user_templates):
        return False

    _save_user_templates(new_templates)
    return True
