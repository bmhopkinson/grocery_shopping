"""
Ingredient collation logic for smart reminders.

Handles merging new grocery items with existing reminders list items.
"""

import re
from fractions import Fraction
from typing import Optional

from models import Ingredient


def normalize_name(name: str) -> str:
    """
    Normalize ingredient name for matching.

    - Lowercase
    - Strip whitespace
    - Simple singularization (remove trailing 's' if not 'ss')
    """
    name = name.lower().strip()
    # Simple singularization: eggs -> egg, tomatoes -> tomatoe -> tomato
    if name.endswith('oes'):
        name = name[:-2]
    elif name.endswith('ies'):
        name = name[:-3] + 'y'
    elif name.endswith('es') and not name.endswith('sses'):
        name = name[:-2]
    elif name.endswith('s') and not name.endswith('ss'):
        name = name[:-1]
    return name


def parse_reminder_text(text: str) -> tuple[str, str, str]:
    """
    Parse reminder text back to (name, amount, unit).

    Expected format: "name (amount unit)" or "name (amount)"

    Examples:
        "eggs (3 large)" -> ("eggs", "3", "large")
        "olive oil (2 tablespoons)" -> ("olive oil", "2", "tablespoons")
        "salt (1)" -> ("salt", "1", "")
        "flour (1 cup + 2 tbsp)" -> ("flour", "1 cup + 2 tbsp", "")  # combined format

    Returns:
        Tuple of (name, amount, unit). If parsing fails, returns (text, "", "").
    """
    # Match: name (amount unit) or name (amount)
    match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', text)
    if not match:
        return (text.strip(), "", "")

    name = match.group(1).strip()
    inside_parens = match.group(2).strip()

    # If it contains '+', it's already a combined format - don't split further
    if '+' in inside_parens:
        return (name, inside_parens, "")

    # Try to split into amount and unit
    # Amount is the leading numeric part (including fractions like 1/2)
    amount_match = re.match(r'^([\d./\-]+(?:\s*-\s*[\d./]+)?)\s*(.*)$', inside_parens)
    if amount_match:
        amount = amount_match.group(1).strip()
        unit = amount_match.group(2).strip()
        return (name, amount, unit)

    # If no numeric start, treat whole thing as amount
    return (name, inside_parens, "")


def parse_amount(amount_str: str) -> Optional[float]:
    """
    Parse an amount string to a float.

    Handles: "2", "1/2", "1.5", "1-2" (takes first number)

    Returns None if parsing fails.
    """
    if not amount_str:
        return None

    # Handle ranges like "1-2" - take the first number
    if '-' in amount_str and not amount_str.startswith('-'):
        amount_str = amount_str.split('-')[0].strip()

    try:
        # Try as fraction first (handles "1/2")
        return float(Fraction(amount_str))
    except (ValueError, ZeroDivisionError):
        pass

    try:
        return float(amount_str)
    except ValueError:
        return None


def format_amount(value: float) -> str:
    """Format a float amount nicely (no unnecessary decimals)."""
    if value == int(value):
        return str(int(value))
    # Round to 2 decimal places
    return f"{value:.2g}"


def combine_amounts(amt1: str, unit1: str, amt2: str, unit2: str) -> tuple[str, str]:
    """
    Combine two amounts.

    If units match (case-insensitive), add numerically.
    If units differ, concatenate as "amt1 unit1 + amt2 unit2".

    Returns:
        (combined_amount, combined_unit)
    """
    unit1_norm = unit1.lower().strip()
    unit2_norm = unit2.lower().strip()

    # If units match, try to add numerically
    if unit1_norm == unit2_norm:
        val1 = parse_amount(amt1)
        val2 = parse_amount(amt2)

        if val1 is not None and val2 is not None:
            combined = format_amount(val1 + val2)
            return (combined, unit1)  # Keep original unit casing

    # Units differ or couldn't parse - concatenate
    part1 = f"{amt1} {unit1}".strip() if unit1 else amt1
    part2 = f"{amt2} {unit2}".strip() if unit2 else amt2
    return (f"{part1} + {part2}", "")


def collate_ingredients(
    existing: list[str],
    new_items: list[Ingredient]
) -> tuple[list[Ingredient], list[tuple[str, Ingredient]]]:
    """
    Collate new ingredients with existing reminders.

    Args:
        existing: List of reminder texts from the list (e.g., "eggs (3 large)")
        new_items: List of Ingredient objects to add

    Returns:
        Tuple of:
        - items_to_add: New Ingredient objects with no match in existing
        - items_to_update: List of (existing_text, combined_Ingredient) pairs
    """
    # Parse existing items and build lookup by normalized name
    existing_parsed: dict[str, tuple[str, str, str, str]] = {}  # norm_name -> (original_text, name, amount, unit)
    for text in existing:
        name, amount, unit = parse_reminder_text(text)
        norm_name = normalize_name(name)
        # If multiple with same normalized name, keep first
        if norm_name not in existing_parsed:
            existing_parsed[norm_name] = (text, name, amount, unit)

    items_to_add: list[Ingredient] = []
    items_to_update: list[tuple[str, Ingredient]] = []

    for item in new_items:
        norm_name = normalize_name(item.name)

        if norm_name in existing_parsed:
            # Found a match - combine
            orig_text, orig_name, orig_amt, orig_unit = existing_parsed[norm_name]

            combined_amt, combined_unit = combine_amounts(
                orig_amt, orig_unit,
                item.amount, item.unit or ""
            )

            # Create combined ingredient (use original name to maintain consistency)
            combined = Ingredient(
                name=orig_name,
                amount=combined_amt,
                unit=combined_unit
            )
            items_to_update.append((orig_text, combined))

            # Remove from parsed so we don't match again
            del existing_parsed[norm_name]
        else:
            # No match - add as new
            items_to_add.append(item)

    return items_to_add, items_to_update
