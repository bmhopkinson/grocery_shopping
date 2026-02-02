"""
HTML content extraction utilities.

Provides functions for extracting recipe data from HTML pages,
including JSON-LD structured data and plain text content.
"""

import json
from bs4 import BeautifulSoup


def extract_json_ld_recipe(html: str) -> str | None:
    """
    Extract recipe data from JSON-LD structured data if present.

    Args:
        html: Raw HTML content of the page

    Returns:
        JSON string of recipe data, or None if not found
    """
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)

            # Handle both single objects and arrays
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Recipe":
                        return json.dumps(item, indent=2)
            elif isinstance(data, dict):
                if data.get("@type") == "Recipe":
                    return json.dumps(data, indent=2)
                # Check @graph array
                if "@graph" in data:
                    for item in data["@graph"]:
                        if item.get("@type") == "Recipe":
                            return json.dumps(item, indent=2)
        except (json.JSONDecodeError, TypeError):
            continue

    return None


def extract_text_content(html: str) -> str:
    """
    Extract clean text content from HTML.

    Removes scripts, styles, navigation, headers, and footers,
    then extracts the remaining text content.

    Args:
        html: Raw HTML content of the page

    Returns:
        Cleaned text content with normalized whitespace
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "header", "footer"]):
        element.decompose()

    text = soup.get_text(separator="\n")
    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
