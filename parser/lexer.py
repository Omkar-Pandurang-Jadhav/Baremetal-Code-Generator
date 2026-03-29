"""Lexer module for the STM32F103VB prompt parser.

Tokenizes natural language input into structured tokens
for downstream parsing. Handles pin references, peripheral names,
functions, modes, speeds, and action verbs.
"""

import re
from typing import List

from parser.schema import Token
from parser.hardware_rules import VALID_PERIPHERALS, PERIPHERAL_FUNCTIONS


# Pin pattern: P followed by port letter and pin number (e.g., PA5, PB12)
PIN_PATTERN = re.compile(r'\bP([A-E])(\d{1,2})\b', re.IGNORECASE)

# Peripheral pattern: matches known peripheral names
PERIPHERAL_NAMES = sorted(VALID_PERIPHERALS - {"GPIO"}, key=len, reverse=True)
PERIPHERAL_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(p) for p in PERIPHERAL_NAMES) + r')\b',
    re.IGNORECASE
)

# Collect all peripheral function names
ALL_FUNCTIONS = set()
for funcs in PERIPHERAL_FUNCTIONS.values():
    ALL_FUNCTIONS.update(funcs)
FUNCTION_PATTERN = re.compile(
    r'\b(' + '|'.join(sorted(ALL_FUNCTIONS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE
)

# GPIO keyword
GPIO_PATTERN = re.compile(r'\bGPIO\b', re.IGNORECASE)

# Mode patterns
MODE_PATTERN = re.compile(r'\b(input|output|alternate|analog)\b', re.IGNORECASE)

# Output type patterns
OUTPUT_TYPE_PATTERN = re.compile(r'\b(push-pull|open-drain)\b', re.IGNORECASE)

# Speed pattern
SPEED_PATTERN = re.compile(r'\b(\d+)\s*MHz\b', re.IGNORECASE)

# Pull configuration
PULL_PATTERN = re.compile(r'\b(pull-up|pull-down|floating)\b', re.IGNORECASE)

# Action verbs for configuration
ACTION_PATTERN = re.compile(
    r'\b(configure|enable|setup|initialize|set|init)\b',
    re.IGNORECASE
)


def tokenize(text: str) -> List[Token]:
    """Tokenize the input text into a list of Token objects.

    Scans the input for pins, peripherals, functions, modes,
    speeds, output types, pull configs, and action verbs.

    Args:
        text: The natural language input string.

    Returns:
        List of Token objects sorted by position in the text.
    """
    tokens = []

    # Extract pins
    for match in PIN_PATTERN.finditer(text):
        pin_value = match.group(0).upper()
        tokens.append(Token(type="PIN", value=pin_value, position=match.start()))

    # Extract peripherals (non-GPIO)
    for match in PERIPHERAL_PATTERN.finditer(text):
        value = match.group(0).upper()
        tokens.append(Token(type="PERIPHERAL", value=value, position=match.start()))

    # Extract GPIO keyword
    for match in GPIO_PATTERN.finditer(text):
        # Only add if not already captured as part of a peripheral
        tokens.append(Token(type="PERIPHERAL", value="GPIO", position=match.start()))

    # Extract peripheral functions (TX, RX, MOSI, etc.)
    for match in FUNCTION_PATTERN.finditer(text):
        value = match.group(0).upper()
        tokens.append(Token(type="FUNCTION", value=value, position=match.start()))

    # Extract modes
    for match in MODE_PATTERN.finditer(text):
        tokens.append(Token(type="MODE", value=match.group(0).lower(), position=match.start()))

    # Extract output types
    for match in OUTPUT_TYPE_PATTERN.finditer(text):
        tokens.append(Token(type="OUTPUT_TYPE", value=match.group(0).lower(), position=match.start()))

    # Extract speeds
    for match in SPEED_PATTERN.finditer(text):
        speed_val = f"{match.group(1)}MHz"
        tokens.append(Token(type="SPEED", value=speed_val, position=match.start()))

    # Extract pull configurations
    for match in PULL_PATTERN.finditer(text):
        tokens.append(Token(type="PULL", value=match.group(0).lower(), position=match.start()))

    # Extract action verbs
    for match in ACTION_PATTERN.finditer(text):
        tokens.append(Token(type="ACTION", value=match.group(0).lower(), position=match.start()))

    # Sort tokens by their position in the text
    tokens.sort(key=lambda t: t.position)

    return tokens
