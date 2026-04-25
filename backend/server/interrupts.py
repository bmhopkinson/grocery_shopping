"""
Interrupt type registry and handlers for the meal planner SSE stream.

This module provides a registry pattern for detecting and handling
different types of graph interrupts. Each interrupt type has a
corresponding matcher that detects it and builds the SSE event.

To add a new interrupt type:
1. Add a new value to InterruptType enum
2. Create a new matcher class implementing the Matcher protocol
3. Add the matcher to INTERRUPT_MATCHERS list (before GenericInterruptMatcher)
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Protocol, Any


logger = logging.getLogger(__name__)


class InterruptType(str, Enum):
    """Enumeration of known interrupt types."""
    MEAL_SELECTION = "meal_options"
    INGREDIENT_REVIEW = "ingredient_review"
    REMINDERS_PROMPT = "reminders_prompt"
    GENERIC = "interrupt"


@dataclass
class InterruptMatch:
    """Result of matching an interrupt to a handler."""
    interrupt_type: InterruptType
    event_name: str
    event_data: dict


class InterruptMatcher(Protocol):
    """Protocol for interrupt matchers."""

    def matches(
        self,
        next_node: str | None,
        instruction: str,
        interrupt_value: dict | None
    ) -> bool:
        """Return True if this matcher handles the interrupt."""
        ...

    def build_event(self, interrupt_value: dict | None) -> InterruptMatch:
        """Build the SSE event data for this interrupt."""
        ...


class MealSelectionMatcher:
    """Matcher for meal selection interrupt (present_options node)."""

    KEYWORDS = {"select a recipe", "1-5"}
    NODES = {"present_options"}

    def matches(
        self,
        next_node: str | None,
        instruction: str,
        interrupt_value: dict | None
    ) -> bool:
        # Match by node name (most reliable)
        if next_node in self.NODES:
            return True
        # Check for "options" key in interrupt value (meal selection has options list)
        if interrupt_value and "options" in interrupt_value and interrupt_value["options"]:
            return True
        # Fallback to keyword matching (for subgraphs that may rename nodes)
        instruction_lower = instruction.lower()
        return any(kw in instruction_lower for kw in self.KEYWORDS)

    def build_event(self, interrupt_value: dict | None) -> InterruptMatch:
        iv = interrupt_value or {}
        return InterruptMatch(
            interrupt_type=InterruptType.MEAL_SELECTION,
            event_name="meal_options",
            event_data={
                "options": iv.get("options", []),
                "prompt": iv.get("prompt", "Select a meal:"),
                "instruction": iv.get("instruction", "")
            }
        )


class IngredientReviewMatcher:
    """Matcher for ingredient review interrupt (review_ingredients node)."""

    KEYWORDS = {"remove", "approve", "'ok'"}

    def matches(
        self,
        next_node: str | None,
        instruction: str,
        interrupt_value: dict | None
    ) -> bool:
        instruction_lower = instruction.lower()
        return any(kw in instruction_lower for kw in self.KEYWORDS)

    def build_event(self, interrupt_value: dict | None) -> InterruptMatch:
        iv = interrupt_value or {}
        return InterruptMatch(
            interrupt_type=InterruptType.INGREDIENT_REVIEW,
            event_name="ingredient_review",
            event_data={
                "ingredients": iv.get("ingredients", []),
                "prompt": iv.get("prompt", "Review ingredients:"),
                "instruction": iv.get("instruction", "")
            }
        )


class RemindersPromptMatcher:
    """Matcher for reminders list selection interrupt (add_to_reminders node)."""

    KEYWORDS = {"list number", "skip", "list name"}
    NODES = {"add_to_reminders"}

    def matches(
        self,
        next_node: str | None,
        instruction: str,
        interrupt_value: dict | None
    ) -> bool:
        # Match by node name (most reliable)
        if next_node in self.NODES:
            return True
        # Check for "existing_lists" key (unique to reminders prompt)
        if interrupt_value and "existing_lists" in interrupt_value:
            return True
        # Fallback to keyword matching
        instruction_lower = instruction.lower()
        return any(kw in instruction_lower for kw in self.KEYWORDS)

    def build_event(self, interrupt_value: dict | None) -> InterruptMatch:
        iv = interrupt_value or {}
        return InterruptMatch(
            interrupt_type=InterruptType.REMINDERS_PROMPT,
            event_name="reminders_prompt",
            event_data={
                "items": iv.get("items", []),
                "existing_lists": iv.get("existing_lists", []),
                "prompt": iv.get("prompt", "Select a reminders list:"),
                "instruction": iv.get("instruction", "")
            }
        )


class GenericInterruptMatcher:
    """Fallback matcher for unknown interrupt types."""

    def matches(
        self,
        next_node: str | None,
        instruction: str,
        interrupt_value: dict | None
    ) -> bool:
        # Always matches as the final fallback
        return True

    def build_event(self, interrupt_value: dict | None) -> InterruptMatch:
        iv = interrupt_value or {}
        return InterruptMatch(
            interrupt_type=InterruptType.GENERIC,
            event_name="interrupt",
            event_data={
                "next_node": None,  # Will be filled in by caller if needed
                "prompt": iv.get("prompt", "Input required:"),
                "data": iv
            }
        )


# Registry of matchers in priority order
# More specific matchers should come first
# GenericInterruptMatcher must be last as it always matches
INTERRUPT_MATCHERS: list[Any] = [
    RemindersPromptMatcher(),  # Check first - has unique "existing_lists" key
    IngredientReviewMatcher(),
    MealSelectionMatcher(),
    GenericInterruptMatcher(),
]


def detect_interrupt(
    next_node: str | None,
    interrupt_value: dict | None
) -> InterruptMatch:
    """
    Detect the interrupt type and build the appropriate SSE event.

    Uses the registry pattern to match against known interrupt patterns.
    Iterates through matchers in order until one matches.

    Args:
        next_node: The name of the next node that will execute after resume
        interrupt_value: The value passed to interrupt() in the node

    Returns:
        InterruptMatch with the event type and data
    """
    instruction = ""
    if interrupt_value:
        instruction = interrupt_value.get("instruction", "")

    logger.debug(f"detect_interrupt: next_node={next_node}, instruction={instruction!r}")
    logger.debug(f"detect_interrupt: interrupt_value keys={list(interrupt_value.keys()) if interrupt_value else None}")

    for matcher in INTERRUPT_MATCHERS:
        if matcher.matches(next_node, instruction, interrupt_value):
            match = matcher.build_event(interrupt_value)
            logger.debug(f"detect_interrupt: matched {type(matcher).__name__} -> event={match.event_name}")
            # For generic interrupts, add the next_node info
            if match.interrupt_type == InterruptType.GENERIC:
                match.event_data["next_node"] = next_node
            return match

    # Should never reach here due to GenericInterruptMatcher
    raise RuntimeError("No interrupt matcher found - this should not happen")
