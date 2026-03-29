"""Parser module for the STM32F103VB prompt parser.

Converts tokenized input into structured hardware configuration intents.
Handles pin list expansion (Problem 1) and multi-function peripheral
parsing (Problem 2).
"""

import re
from typing import List, Optional

from parser.schema import Token, Intent
from parser.lexer import tokenize
from parser.hardware_rules import (
    VALID_PERIPHERALS, PERIPHERAL_FUNCTIONS, PERIPHERAL_PIN_MAP,
)


def parse_tokens(tokens: List[Token]) -> List[Intent]:
    """Parse a list of tokens into hardware configuration intents.

    Handles:
    - Simple GPIO configurations with one or multiple pins (Problem 1)
    - Peripheral configurations with explicit pin assignments
    - Multi-function peripheral parsing (Problem 2)

    Args:
        tokens: List of Token objects from the lexer.

    Returns:
        List of Intent objects representing hardware configurations.
    """
    intents = []

    # Categorize tokens
    pins = [t for t in tokens if t.type == "PIN"]
    peripherals = [t for t in tokens if t.type == "PERIPHERAL"]
    functions = [t for t in tokens if t.type == "FUNCTION"]
    modes = [t for t in tokens if t.type == "MODE"]
    output_types = [t for t in tokens if t.type == "OUTPUT_TYPE"]
    speeds = [t for t in tokens if t.type == "SPEED"]
    pulls = [t for t in tokens if t.type == "PULL"]

    # Determine the primary peripheral
    peripheral_name = None
    for p in peripherals:
        if p.value != "GPIO":
            peripheral_name = p.value
            break

    if peripheral_name is None:
        # Check if GPIO is explicitly mentioned or if it's implied
        if peripherals:
            peripheral_name = "GPIO"
        elif pins and not functions:
            # Pins without peripheral or functions → GPIO
            peripheral_name = "GPIO"

    # Get shared configuration properties
    mode = modes[0].value if modes else None
    output_type = output_types[0].value if output_types else None
    speed = speeds[0].value if speeds else None
    pull = pulls[0].value if pulls else None

    # Case 1: Non-GPIO peripheral with functions (Problem 2)
    if peripheral_name and peripheral_name != "GPIO" and functions:
        intents.extend(
            _parse_peripheral_with_functions(
                peripheral_name, functions, pins, tokens,
                mode, output_type, speed, pull
            )
        )
    # Case 2: Non-GPIO peripheral without functions (e.g., "ADC1 on PA0")
    elif peripheral_name and peripheral_name != "GPIO" and not functions:
        for pin in pins:
            intents.append(Intent(
                peripheral=peripheral_name,
                pin=pin.value,
                mode=mode,
                output_type=output_type,
                speed=speed,
                pull=pull,
            ))
    # Case 3: GPIO with multiple pins (Problem 1)
    elif peripheral_name == "GPIO" or (pins and not peripheral_name):
        for pin in pins:
            intents.append(Intent(
                peripheral="GPIO",
                pin=pin.value,
                mode=mode or "output",
                output_type=output_type,
                speed=speed,
                pull=pull,
            ))

    return intents


def _parse_peripheral_with_functions(
    peripheral: str,
    functions: List[Token],
    pins: List[Token],
    all_tokens: List[Token],
    mode: Optional[str],
    output_type: Optional[str],
    speed: Optional[str],
    pull: Optional[str],
) -> List[Intent]:
    """Parse a peripheral with multiple function assignments.

    Matches each function token to its nearest following pin token
    to handle prompts like:
    "SPI1 with MOSI on PA7, MISO on PA6, SCK on PA5 and NSS on PA4"

    Args:
        peripheral: The peripheral name (e.g., 'SPI1').
        functions: List of function tokens.
        pins: List of pin tokens.
        all_tokens: All tokens for positional analysis.
        mode, output_type, speed, pull: Shared configuration properties.

    Returns:
        List of Intent objects, one per function-pin pair.
    """
    intents = []

    # Build a position-sorted list of function and pin tokens
    func_pin_tokens = sorted(
        [t for t in all_tokens if t.type in ("FUNCTION", "PIN")],
        key=lambda t: t.position
    )

    # Match each function to its nearest following pin
    used_pins = set()
    for i, token in enumerate(func_pin_tokens):
        if token.type == "FUNCTION":
            func_name = token.value
            # Find the next pin token after this function
            pin_value = None
            for j in range(i + 1, len(func_pin_tokens)):
                if func_pin_tokens[j].type == "PIN":
                    candidate = func_pin_tokens[j].value
                    if candidate not in used_pins:
                        pin_value = candidate
                        used_pins.add(candidate)
                        break

            if pin_value is None:
                # Try to use the default pin mapping
                default_pins = PERIPHERAL_PIN_MAP.get(peripheral, {})
                pin_value = default_pins.get(func_name)

            if pin_value:
                intents.append(Intent(
                    peripheral=peripheral,
                    pin=pin_value,
                    function=func_name,
                    mode=mode or "alternate",
                    output_type=output_type,
                    speed=speed,
                    pull=pull,
                ))

    # Handle any remaining pins not matched to functions
    if not intents and pins:
        for pin in pins:
            intents.append(Intent(
                peripheral=peripheral,
                pin=pin.value,
                mode=mode,
                output_type=output_type,
                speed=speed,
                pull=pull,
            ))

    return intents


def parse_sub_prompt(text: str) -> List[Intent]:
    """Parse a single sub-prompt string into intents.

    Tokenizes the text and then parses the tokens.

    Args:
        text: A single sub-prompt string.

    Returns:
        List of Intent objects.
    """
    tokens = tokenize(text)
    return parse_tokens(tokens)
