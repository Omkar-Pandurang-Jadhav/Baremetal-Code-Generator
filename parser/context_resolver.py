"""Context resolver module for the STM32F103VB prompt parser.

Resolves peripheral context inheritance across clauses within
a sub-prompt. When a clause mentions a peripheral function (e.g., RX)
without an explicit peripheral name, the resolver inherits the
peripheral from the preceding clause.

This module handles Problem 3: Peripheral Context Inheritance.
"""

import re
from typing import List, Optional

from parser.schema import Token
from parser.hardware_rules import PERIPHERAL_FUNCTIONS


# All known peripheral function names
ALL_FUNCTIONS = set()
for funcs in PERIPHERAL_FUNCTIONS.values():
    ALL_FUNCTIONS.update(funcs)


def resolve_context(sub_prompt: str) -> str:
    """Resolve peripheral context inheritance within a sub-prompt.

    If a sub-prompt contains multiple function references with only
    one peripheral name, propagate that peripheral to all function
    references.

    Example:
        "enable USART1 TX on PA9 and RX on PA10"
        → The 'RX on PA10' clause inherits USART1 context.

    This is done by analyzing the sub-prompt text and ensuring
    peripheral names are present before each function reference.

    Args:
        sub_prompt: A single sub-prompt string.

    Returns:
        The sub-prompt with peripheral context resolved.
    """
    # Find the peripheral mentioned in this sub-prompt
    peripheral = _find_peripheral(sub_prompt)
    if not peripheral:
        return sub_prompt

    # Find function keywords that lack an immediately preceding peripheral
    result = _inject_peripheral_context(sub_prompt, peripheral)
    return result


def _find_peripheral(text: str) -> Optional[str]:
    """Find the first peripheral name in the text (excluding GPIO)."""
    from parser.hardware_rules import VALID_PERIPHERALS

    peripheral_names = sorted(
        (VALID_PERIPHERALS - {"GPIO"}),
        key=len, reverse=True
    )
    pattern = re.compile(
        r'\b(' + '|'.join(re.escape(p) for p in peripheral_names) + r')\b',
        re.IGNORECASE
    )
    match = pattern.search(text)
    if match:
        return match.group(0).upper()
    return None


def _inject_peripheral_context(text: str, peripheral: str) -> str:
    """Inject peripheral name before function keywords that lack one.

    Scans for function keywords (TX, RX, MOSI, etc.) and checks if
    the peripheral name appears just before them. If not, inserts it.

    Args:
        text: The sub-prompt text.
        peripheral: The peripheral name to inject (e.g., 'USART1').

    Returns:
        Text with peripheral context injected where needed.
    """
    # Get valid functions for this peripheral
    valid_funcs = PERIPHERAL_FUNCTIONS.get(peripheral, [])
    if not valid_funcs:
        return text

    func_pattern = re.compile(
        r'\b(' + '|'.join(re.escape(f) for f in valid_funcs) + r')\b',
        re.IGNORECASE
    )

    peripheral_pattern = re.compile(
        r'\b' + re.escape(peripheral) + r'\b',
        re.IGNORECASE
    )

    # Find all function matches
    result = text
    offset = 0
    # Allow a small buffer beyond the peripheral name length for whitespace/punctuation
    LOOKBACK_BUFFER = 5

    for match in func_pattern.finditer(text):
        pos = match.start()
        # Check if peripheral name appears shortly before this function
        lookback_start = max(0, pos - len(peripheral) - LOOKBACK_BUFFER)
        lookback_text = text[lookback_start:pos]

        if not peripheral_pattern.search(lookback_text):
            # Need to inject the peripheral name before this function
            insert_pos = match.start() + offset
            injection = f"{peripheral} "
            result = result[:insert_pos] + injection + result[insert_pos:]
            offset += len(injection)

    return result
