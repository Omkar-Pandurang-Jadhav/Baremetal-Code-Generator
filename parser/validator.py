"""Validator module for the STM32F103VB prompt parser.

Validates parsed intents against hardware rules to ensure
configurations are valid for the STM32F103VB microcontroller.
"""

from typing import List

from parser.schema import Intent, ParseResult
from parser.hardware_rules import (
    VALID_PINS,
    VALID_PERIPHERALS,
    PERIPHERAL_FUNCTIONS,
    PERIPHERAL_PIN_MAP,
    VALID_MODES,
    VALID_OUTPUT_TYPES,
    VALID_SPEEDS,
    VALID_PULL,
)


def validate_intents(intents: List[Intent]) -> ParseResult:
    """Validate a list of intents against STM32F103VB hardware rules.

    Checks:
    - Pin validity
    - Peripheral validity
    - Function validity for the peripheral
    - Pin-peripheral compatibility
    - Mode, output type, speed, and pull validity

    Args:
        intents: List of Intent objects to validate.

    Returns:
        ParseResult with validated intents, warnings, and errors.
    """
    result = ParseResult()

    for intent in intents:
        errors = []
        warnings = []

        # Validate pin
        if intent.pin not in VALID_PINS:
            errors.append(f"Invalid pin: {intent.pin}")

        # Validate peripheral
        if intent.peripheral not in VALID_PERIPHERALS:
            errors.append(f"Invalid peripheral: {intent.peripheral}")

        # Validate function for peripheral
        if intent.function:
            valid_funcs = PERIPHERAL_FUNCTIONS.get(intent.peripheral, [])
            if valid_funcs and intent.function not in valid_funcs:
                errors.append(
                    f"Invalid function '{intent.function}' for "
                    f"peripheral {intent.peripheral}"
                )

        # Validate pin-peripheral mapping (warning only)
        if intent.function and intent.peripheral in PERIPHERAL_PIN_MAP:
            expected_pin = PERIPHERAL_PIN_MAP[intent.peripheral].get(
                intent.function
            )
            if expected_pin and expected_pin != intent.pin:
                warnings.append(
                    f"Pin {intent.pin} is not the default pin for "
                    f"{intent.peripheral} {intent.function} "
                    f"(expected {expected_pin})"
                )

        # Validate mode
        if intent.mode and intent.mode not in VALID_MODES:
            errors.append(f"Invalid mode: {intent.mode}")

        # Validate output type
        if intent.output_type and intent.output_type not in VALID_OUTPUT_TYPES:
            errors.append(f"Invalid output type: {intent.output_type}")

        # Validate speed
        if intent.speed and intent.speed not in VALID_SPEEDS:
            errors.append(f"Invalid speed: {intent.speed}")

        # Validate pull
        if intent.pull and intent.pull not in VALID_PULL:
            errors.append(f"Invalid pull configuration: {intent.pull}")

        if errors:
            result.errors.extend(errors)
        else:
            result.intents.append(intent)
            result.warnings.extend(warnings)

    return result
