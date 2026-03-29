"""Prompt splitter module for the STM32F103VB prompt parser.

Splits complex multi-intent prompts into individual sub-prompts
based on intent verbs and peripheral keywords, preserving
peripheral context across clauses.

This module handles Problem 5: Improve Prompt Splitting.
"""

import re
from typing import List

from parser.hardware_rules import VALID_PERIPHERALS


# Intent verb pattern
INTENT_VERBS = re.compile(
    r'\b(configure|enable|setup|initialize|set|init)\b',
    re.IGNORECASE
)

# Peripheral name pattern (non-GPIO)
_peripheral_names = sorted(
    (VALID_PERIPHERALS - {"GPIO"}),
    key=len, reverse=True
)
PERIPHERAL_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(p) for p in _peripheral_names) + r')\b',
    re.IGNORECASE
)

# Pin pattern
PIN_PATTERN = re.compile(r'\bP[A-E]\d{1,2}\b', re.IGNORECASE)

# Peripheral function keywords
FUNC_PATTERN = re.compile(
    r'\b(TX|RX|MOSI|MISO|SCK|NSS|SDA|SCL|CK|CTS|RTS|'
    r'CH1|CH2|CH3|CH4|IN[0-7])\b',
    re.IGNORECASE
)


def split_prompt(text: str) -> List[str]:
    """Split a complex prompt into individual sub-prompts.

    Splits on commas and 'and' conjunctions, but only at intent boundaries.
    Preserves peripheral context so that clauses like
    'TX on PA9 and RX on PA10' stay together when they share a peripheral.

    Args:
        text: The full user prompt string.

    Returns:
        List of sub-prompt strings.
    """
    # First, split on explicit sentence-level separators:
    # commas followed by intent verbs, or 'and' followed by intent verbs
    # This handles: "Configure PA5 ..., enable USART1 ..., and setup ADC1..."

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text.strip())

    # Split on comma or 'and' that is followed by an intent verb
    # Pattern: , and <verb> | , <verb> | and <verb> (only at clause boundaries)
    parts = _split_on_intent_boundaries(text)

    return [p.strip() for p in parts if p.strip()]


def _split_on_intent_boundaries(text: str) -> List[str]:
    """Split text at boundaries where a new intent verb begins a new clause.

    A boundary is a comma or 'and' conjunction followed by an intent verb,
    or a comma/'and' followed by a new peripheral keyword (indicating a
    new peripheral context).

    This preserves intra-peripheral clauses like:
    'USART1 TX on PA9 and RX on PA10' (should NOT split between TX and RX
    when both belong to USART1).
    """
    # Strategy: find potential split points (commas, 'and'), then decide
    # whether to split based on what follows.

    # We look for patterns like:
    #   ", and <verb>"   → split
    #   ", <verb>"       → split
    #   "and <verb>"     → split (only if preceded by comma-like context)
    #   ", and <peripheral>" → split
    #   ", <peripheral>" → split

    # But NOT: "and <function>" when a peripheral is active
    #   e.g., "TX on PA9 and RX on PA10" → do NOT split

    result = []
    # Use a regex to find split candidates
    # Split pattern: (,\s*and\s+|\s*,\s*|\s+and\s+) followed by context
    split_pattern = re.compile(
        r'(?:,\s*and\s+|,\s+|\s+and\s+)',
        re.IGNORECASE
    )

    candidates = list(split_pattern.finditer(text))
    if not candidates:
        return [text]

    prev_end = 0
    segments = []

    for match in candidates:
        before = text[prev_end:match.start()]
        segments.append((before, match))
        prev_end = match.end()

    # Add the trailing text
    trailing = text[prev_end:]

    # Now decide which splits to keep
    result_parts = []
    current = ""

    for i, (segment, sep_match) in enumerate(segments):
        current += segment
        after_sep = text[sep_match.end():]

        # Check what follows the separator
        should_split = _should_split_here(after_sep, current)

        if should_split:
            result_parts.append(current.strip())
            current = ""
        else:
            # Keep the conjunction text (but simplified)
            current += " and "

    # Add the trailing part
    current += trailing
    if current.strip():
        result_parts.append(current.strip())

    return result_parts


def _should_split_here(after_text: str, before_text: str) -> bool:
    """Determine if we should split at this conjunction point.

    Split if what follows starts with an intent verb or a new peripheral.
    Don't split if what follows is just a function name (TX, RX, MOSI, etc.)
    that belongs to the same peripheral context.
    """
    after_stripped = after_text.strip()

    # If followed by an intent verb → always split
    if INTENT_VERBS.match(after_stripped):
        return True

    # If followed by a peripheral name → split
    if PERIPHERAL_PATTERN.match(after_stripped):
        return True

    # If followed by GPIO keyword → split
    if re.match(r'\bGPIO\b', after_stripped, re.IGNORECASE):
        return True

    # If followed by a function keyword (TX, RX, MOSI, etc.) → DON'T split
    # This preserves "TX on PA9 and RX on PA10" within the same peripheral
    if FUNC_PATTERN.match(after_stripped):
        return False

    # If followed by a pin directly → don't split (keep pin lists together)
    # e.g., "PA5, PA6" in a pin list should NOT split (handled by parser)
    if PIN_PATTERN.match(after_stripped):
        return False

    return False
