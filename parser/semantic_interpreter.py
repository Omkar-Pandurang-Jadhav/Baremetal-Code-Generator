"""Semantic interpreter module for the STM32F103VB prompt parser.

Provides a preprocessing layer that maps common natural language actions
to explicit hardware configuration verbs before parsing.

This module handles Problem 4: Natural Language Action Mapping.

Examples:
    "Blink LED on PA5"          → "configure GPIO output on PA5"
    "Read ADC value from PA0"   → "configure ADC input on PA0"
    "Send data through USART1"  → "configure USART1 TX"
"""

import re
from typing import List, Tuple


# Mapping of natural language action patterns to configuration intents.
# Each entry: (regex pattern, replacement template)
# The replacement uses {rest} as a placeholder for the remaining text.
ACTION_MAPPINGS: List[Tuple[re.Pattern, str]] = [
    # LED / blink actions → GPIO output
    (
        re.compile(r'\bblink\s+(?:an?\s+)?LED\b', re.IGNORECASE),
        "configure GPIO output"
    ),
    (
        re.compile(r'\btoggle\s+(?:an?\s+)?LED\b', re.IGNORECASE),
        "configure GPIO output"
    ),
    (
        re.compile(r'\bturn\s+(?:on|off)\s+(?:an?\s+)?LED\b', re.IGNORECASE),
        "configure GPIO output"
    ),
    (
        re.compile(r'\blight\s+(?:up\s+)?(?:an?\s+)?LED\b', re.IGNORECASE),
        "configure GPIO output"
    ),
    # Read ADC → configure ADC input
    (
        re.compile(r'\bread\s+(?:an?\s+)?ADC\s+(?:value|reading|data)\s*(?:from|on)?\b', re.IGNORECASE),
        "configure ADC1"
    ),
    (
        re.compile(r'\bread\s+(?:an?\s+)?ADC\b', re.IGNORECASE),
        "configure ADC1"
    ),
    (
        re.compile(r'\bsample\s+(?:an?\s+)?ADC\b', re.IGNORECASE),
        "configure ADC1"
    ),
    # Send data via USART → configure USART TX
    (
        re.compile(
            r'\bsend\s+(?:\w+\s+)*(?:through|via|over|on)\s+(USART\d*)\s+(TX)\b',
            re.IGNORECASE
        ),
        None  # Special handler
    ),
    (
        re.compile(
            r'\bsend\s+(?:\w+\s+)*(?:through|via|over|on)\s+(USART\d*)\b',
            re.IGNORECASE
        ),
        None  # Special handler
    ),
    # Receive data via USART → configure USART RX
    (
        re.compile(
            r'\breceive\s+(?:\w+\s+)*(?:through|via|over|on|from)\s+(USART\d*)\b',
            re.IGNORECASE
        ),
        None  # Special handler
    ),
    # Read sensor / button → GPIO input
    (
        re.compile(r'\bread\s+(?:a\s+)?(?:sensor|button|switch)\b', re.IGNORECASE),
        "configure GPIO input"
    ),
    # Drive / control motor/relay → GPIO output
    (
        re.compile(r'\b(?:drive|control)\s+(?:a\s+)?(?:motor|relay|buzzer)\b', re.IGNORECASE),
        "configure GPIO output"
    ),
]

# Pattern to detect "send ... ADC readings through USART1 TX on PA9"
SEND_ADC_USART_PATTERN = re.compile(
    r'\bsend\s+(?:\w+\s+)*(?:readings?|data|values?)\s+(?:through|via|over|on)\s+'
    r'(USART\d*)\s+(TX)\b',
    re.IGNORECASE
)

SEND_USART_PATTERN = re.compile(
    r'\bsend\s+(?:\w+\s+)*(?:through|via|over|on)\s+(USART\d*)\b',
    re.IGNORECASE
)

RECEIVE_USART_PATTERN = re.compile(
    r'\breceive\s+(?:\w+\s+)*(?:through|via|over|on|from)\s+(USART\d*)\b',
    re.IGNORECASE
)


def interpret(text: str) -> str:
    """Interpret natural language actions and convert to explicit config commands.

    Preprocesses the input text, replacing natural language action phrases
    with explicit hardware configuration verbs that the parser can understand.

    Args:
        text: The raw user input string.

    Returns:
        The preprocessed string with action phrases replaced.
    """
    result = text

    # Handle "send ... through USART1 TX on PIN" patterns
    match = SEND_ADC_USART_PATTERN.search(result)
    if match:
        peripheral = match.group(1).upper()
        func = match.group(2).upper()
        # Replace the send phrase with configure
        before = result[:match.start()]
        after = result[match.end():]
        result = f"{before}configure {peripheral} {func}{after}"
        return result

    # Handle "send ... through USART1" (without explicit TX)
    match = SEND_USART_PATTERN.search(result)
    if match:
        peripheral = match.group(1).upper()
        before = result[:match.start()]
        after = result[match.end():]
        result = f"{before}configure {peripheral} TX{after}"
        return result

    # Handle "receive ... from USART1"
    match = RECEIVE_USART_PATTERN.search(result)
    if match:
        peripheral = match.group(1).upper()
        before = result[:match.start()]
        after = result[match.end():]
        result = f"{before}configure {peripheral} RX{after}"
        return result

    # Apply simple pattern replacements
    for pattern, replacement in ACTION_MAPPINGS:
        if replacement is None:
            continue
        match = pattern.search(result)
        if match:
            before = result[:match.start()]
            after = result[match.end():]
            result = f"{before}{replacement}{after}"

    return result
