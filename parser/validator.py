"""
Semantic validation layer for the STM32 prompt parser.

Validates parsed configuration objects against STM32F103VB hardware rules
derived from RM0008 reference manual and the STM32F103VB datasheet.
"""

from __future__ import annotations

from typing import List

from . import hardware_rules as hw
from .schema import (
    ADCConfig,
    EXTIConfig,
    GPIOConfig,
    I2CConfig,
    ParsedIntent,
    RCCConfig,
    SPIConfig,
    TimerConfig,
    USARTConfig,
)


class ValidationError(Exception):
    """Raised when a parsed configuration violates hardware constraints."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate(intent: ParsedIntent) -> ParsedIntent:
    """
    Validate *intent* against STM32F103VB hardware rules.

    Returns the (possibly unchanged) intent on success, raises
    :class:`ValidationError` if any constraint is violated.
    """
    errors: List[str] = []

    # MCU check
    if intent.mcu not in hw.SUPPORTED_MCUS:
        errors.append(f"Unsupported MCU: {intent.mcu}")

    # Peripheral check
    if intent.peripheral not in hw.SUPPORTED_PERIPHERALS:
        errors.append(f"Unsupported peripheral: {intent.peripheral}")

    # Dispatch to peripheral-specific validation
    cfg = intent.configuration
    if isinstance(cfg, GPIOConfig):
        _validate_gpio(cfg, errors)
    elif isinstance(cfg, USARTConfig):
        _validate_usart(cfg, errors)
    elif isinstance(cfg, TimerConfig):
        _validate_timer(cfg, errors)
    elif isinstance(cfg, ADCConfig):
        _validate_adc(cfg, errors)
    elif isinstance(cfg, SPIConfig):
        _validate_spi(cfg, errors)
    elif isinstance(cfg, I2CConfig):
        _validate_i2c(cfg, errors)
    elif isinstance(cfg, EXTIConfig):
        _validate_exti(cfg, errors)
    elif isinstance(cfg, RCCConfig):
        _validate_rcc(cfg, errors)

    if errors:
        raise ValidationError(errors)

    return intent


# ---------------------------------------------------------------------------
# Peripheral-specific validators
# ---------------------------------------------------------------------------

def _validate_gpio(cfg: GPIOConfig, errors: List[str]) -> None:
    if cfg.port not in hw.VALID_GPIO_PORTS:
        errors.append(
            f"Invalid GPIO port '{cfg.port}'. "
            f"Valid ports: {sorted(hw.VALID_GPIO_PORTS)}"
        )
    if not (hw.VALID_PIN_RANGE[0] <= cfg.pin <= hw.VALID_PIN_RANGE[1]):
        errors.append(
            f"Pin {cfg.pin} out of range "
            f"({hw.VALID_PIN_RANGE[0]}–{hw.VALID_PIN_RANGE[1]})"
        )
    if cfg.mode not in hw.VALID_GPIO_MODES:
        errors.append(f"Invalid GPIO mode: {cfg.mode}")
    if cfg.mode == "output":
        if cfg.output_type and cfg.output_type not in hw.VALID_OUTPUT_TYPES:
            errors.append(f"Invalid output type: {cfg.output_type}")
        if cfg.speed_mhz is not None and cfg.speed_mhz not in hw.VALID_SPEEDS_MHZ:
            errors.append(
                f"Invalid speed {cfg.speed_mhz} MHz. "
                f"Valid: {sorted(hw.VALID_SPEEDS_MHZ)}"
            )
    if cfg.mode == "input":
        if cfg.input_type and cfg.input_type not in hw.VALID_INPUT_TYPES:
            errors.append(f"Invalid input type: {cfg.input_type}")


def _validate_usart(cfg: USARTConfig, errors: List[str]) -> None:
    key = f"usart{cfg.instance}"
    if key not in hw.VALID_USARTS:
        errors.append(f"Invalid USART instance: {cfg.instance}")
        return
    if cfg.function not in hw.VALID_USART_FUNCTIONS:
        errors.append(f"Invalid USART function: {cfg.function}")
    # Validate pin mapping if port/pin provided
    if cfg.port is not None and cfg.pin is not None:
        valid_pins = hw.AF_PIN_MAP.get((key, cfg.function), set())
        if (cfg.port, cfg.pin) not in valid_pins:
            errors.append(
                f"{key.upper()} {cfg.function.upper()} cannot be mapped to "
                f"P{cfg.port}{cfg.pin}. Valid: "
                f"{_format_pin_set(valid_pins)}"
            )


def _validate_timer(cfg: TimerConfig, errors: List[str]) -> None:
    key = f"tim{cfg.instance}"
    if key not in hw.VALID_TIMERS:
        errors.append(f"Invalid timer instance: {cfg.instance}")
        return
    if cfg.channel is not None and cfg.channel not in hw.VALID_TIMER_CHANNELS:
        errors.append(f"Invalid timer channel: {cfg.channel}")
    if cfg.mode is not None and cfg.mode not in hw.VALID_TIMER_MODES:
        errors.append(f"Invalid timer mode: {cfg.mode}")
    # Validate channel pin mapping
    if cfg.channel is not None and cfg.port is not None and cfg.pin is not None:
        ch_key = f"ch{cfg.channel}"
        valid_pins = hw.AF_PIN_MAP.get((key, ch_key), set())
        if (cfg.port, cfg.pin) not in valid_pins:
            errors.append(
                f"{key.upper()} channel {cfg.channel} cannot be mapped to "
                f"P{cfg.port}{cfg.pin}. Valid: "
                f"{_format_pin_set(valid_pins)}"
            )


def _validate_adc(cfg: ADCConfig, errors: List[str]) -> None:
    key = f"adc{cfg.instance}"
    if key not in hw.VALID_ADCS:
        errors.append(f"Invalid ADC instance: {cfg.instance}")
    if cfg.channel is not None:
        if cfg.channel not in hw.ADC_CHANNEL_PIN_MAP:
            errors.append(f"Invalid ADC channel: {cfg.channel}")
        elif cfg.port is not None and cfg.pin is not None:
            expected = hw.ADC_CHANNEL_PIN_MAP[cfg.channel]
            if (cfg.port, cfg.pin) != expected:
                errors.append(
                    f"ADC channel {cfg.channel} is on "
                    f"P{expected[0]}{expected[1]}, not P{cfg.port}{cfg.pin}"
                )


def _validate_spi(cfg: SPIConfig, errors: List[str]) -> None:
    key = f"spi{cfg.instance}"
    if key not in hw.VALID_SPIS:
        errors.append(f"Invalid SPI instance: {cfg.instance}")
        return
    if cfg.function is not None and cfg.function not in hw.VALID_SPI_FUNCTIONS:
        errors.append(f"Invalid SPI function: {cfg.function}")
    if cfg.function and cfg.port is not None and cfg.pin is not None:
        valid_pins = hw.AF_PIN_MAP.get((key, cfg.function), set())
        if (cfg.port, cfg.pin) not in valid_pins:
            errors.append(
                f"{key.upper()} {cfg.function.upper()} cannot be mapped to "
                f"P{cfg.port}{cfg.pin}. Valid: "
                f"{_format_pin_set(valid_pins)}"
            )


def _validate_i2c(cfg: I2CConfig, errors: List[str]) -> None:
    key = f"i2c{cfg.instance}"
    if key not in hw.VALID_I2CS:
        errors.append(f"Invalid I2C instance: {cfg.instance}")
        return
    if cfg.function is not None and cfg.function not in hw.VALID_I2C_FUNCTIONS:
        errors.append(f"Invalid I2C function: {cfg.function}")
    if cfg.function and cfg.port is not None and cfg.pin is not None:
        valid_pins = hw.AF_PIN_MAP.get((key, cfg.function), set())
        if (cfg.port, cfg.pin) not in valid_pins:
            errors.append(
                f"{key.upper()} {cfg.function.upper()} cannot be mapped to "
                f"P{cfg.port}{cfg.pin}. Valid: "
                f"{_format_pin_set(valid_pins)}"
            )


def _validate_exti(cfg: EXTIConfig, errors: List[str]) -> None:
    if cfg.line not in hw.VALID_EXTI_LINES:
        errors.append(
            f"Invalid EXTI line: {cfg.line}. Must be 0–15."
        )
    if cfg.trigger is not None and cfg.trigger not in hw.VALID_EXTI_TRIGGERS:
        errors.append(f"Invalid EXTI trigger: {cfg.trigger}")


def _validate_rcc(cfg: RCCConfig, errors: List[str]) -> None:
    if cfg.peripheral.lower() not in hw.RCC_CLOCK_MAP:
        errors.append(
            f"Unknown RCC peripheral: {cfg.peripheral}. "
            f"Valid: {sorted(hw.RCC_CLOCK_MAP.keys())}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_pin_set(pins: set) -> str:
    return ", ".join(f"P{p}{n}" for p, n in sorted(pins))
