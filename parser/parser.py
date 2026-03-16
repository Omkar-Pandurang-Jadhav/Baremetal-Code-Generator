"""
Syntax parsing layer for the STM32 prompt parser.

Converts :class:`~parser.lexer.LexerTokens` into validated
:class:`~parser.schema.ParsedIntent` objects by applying peripheral-
detection heuristics and assembling configuration models.
"""

from __future__ import annotations

from typing import List

from . import hardware_rules as hw
from .lexer import LexerTokens, tokenize
from .schema import (
    ADCConfig,
    EXTIConfig,
    GPIOConfig,
    I2CConfig,
    MultiParsedIntent,
    ParsedIntent,
    RCCConfig,
    SPIConfig,
    TimerConfig,
    USARTConfig,
)
from .validator import ValidationError, validate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(prompt: str) -> ParsedIntent:
    """
    Parse a natural-language *prompt* into a single :class:`ParsedIntent`.

    Raises :class:`ValueError` if the prompt cannot be understood, or
    :class:`~parser.validator.ValidationError` if the resulting
    configuration violates hardware constraints.
    """
    tokens = tokenize(prompt)
    intent = _build_intent(tokens)
    return validate(intent)


def parse_multi(prompt: str) -> MultiParsedIntent:
    """
    Parse a prompt that may describe multiple configuration intents.

    Currently delegates to :func:`parse` for single-intent prompts and
    handles I2C dual-pin prompts (e.g. ``PB6 and PB7``).
    """
    tokens = tokenize(prompt)
    intents = _build_intents(tokens)
    validated = [validate(i) for i in intents]
    return MultiParsedIntent(intents=validated)


# ---------------------------------------------------------------------------
# Intent construction
# ---------------------------------------------------------------------------

def _build_intents(tokens: LexerTokens) -> List[ParsedIntent]:
    """Build one or more intents from *tokens*."""
    # I2C with two pins → produce two intents (scl + sda)
    if tokens.i2c_instances and len(tokens.pins) == 2:
        return _build_i2c_dual(tokens)

    return [_build_intent(tokens)]


def _build_intent(tokens: LexerTokens) -> ParsedIntent:
    """Build a single :class:`ParsedIntent` from extracted *tokens*."""

    # Peripheral detection priority:
    #   explicit peripheral instances → GPIO (if pins present)
    if tokens.usart_instances:
        return _build_usart_intent(tokens)
    if tokens.timer_instances:
        return _build_timer_intent(tokens)
    if tokens.adc_instances:
        return _build_adc_intent(tokens)
    if tokens.spi_instances:
        return _build_spi_intent(tokens)
    if tokens.i2c_instances:
        return _build_i2c_intent(tokens)
    if tokens.exti_lines:
        return _build_exti_intent(tokens)
    if tokens.pins or tokens.gpio_ports:
        return _build_gpio_intent(tokens)

    raise ValueError(
        "Could not determine peripheral from prompt. "
        "Please mention a peripheral (GPIO, USART, TIM, ADC, SPI, I2C, EXTI) "
        "or a pin reference (e.g. PA5)."
    )


# ---------------------------------------------------------------------------
# Per-peripheral intent builders
# ---------------------------------------------------------------------------

def _build_gpio_intent(tokens: LexerTokens) -> ParsedIntent:
    if not tokens.pins:
        raise ValueError("GPIO configuration requires at least one pin (e.g. PA5).")
    port, pin = tokens.pins[0]
    mode = tokens.gpio_mode or "output"
    speed = tokens.speeds_mhz[0] if tokens.speeds_mhz else None
    return ParsedIntent(
        peripheral="gpio",
        configuration=GPIOConfig(
            port=port,
            pin=pin,
            mode=mode,
            output_type=tokens.output_type if mode == "output" else None,
            input_type=tokens.input_type if mode == "input" else None,
            speed_mhz=speed if mode in ("output", "alternate_function") else None,
        ),
        clock_enable=tokens.clock_enable,
    )


def _build_usart_intent(tokens: LexerTokens) -> ParsedIntent:
    instance = tokens.usart_instances[0]
    func = tokens.usart_function or "tx"
    port = tokens.pins[0][0] if tokens.pins else None
    pin = tokens.pins[0][1] if tokens.pins else None
    return ParsedIntent(
        peripheral="usart",
        configuration=USARTConfig(
            instance=instance,
            function=func,
            port=port,
            pin=pin,
        ),
        clock_enable=tokens.clock_enable,
    )


def _build_timer_intent(tokens: LexerTokens) -> ParsedIntent:
    instance = tokens.timer_instances[0]
    channel = tokens.timer_channels[0] if tokens.timer_channels else None
    mode = tokens.timer_mode
    port = tokens.pins[0][0] if tokens.pins else None
    pin = tokens.pins[0][1] if tokens.pins else None
    return ParsedIntent(
        peripheral="tim",
        configuration=TimerConfig(
            instance=instance,
            channel=channel,
            mode=mode,
            port=port,
            pin=pin,
        ),
        clock_enable=tokens.clock_enable,
    )


def _build_adc_intent(tokens: LexerTokens) -> ParsedIntent:
    instance = tokens.adc_instances[0]
    port = tokens.pins[0][0] if tokens.pins else None
    pin = tokens.pins[0][1] if tokens.pins else None

    # Resolve ADC channel from pin
    channel = None
    if port is not None and pin is not None:
        for ch, (p, pn) in hw.ADC_CHANNEL_PIN_MAP.items():
            if p == port and pn == pin:
                channel = ch
                break

    return ParsedIntent(
        peripheral="adc",
        configuration=ADCConfig(
            instance=instance,
            channel=channel,
            port=port,
            pin=pin,
        ),
        clock_enable=tokens.clock_enable,
    )


def _build_spi_intent(tokens: LexerTokens) -> ParsedIntent:
    instance = tokens.spi_instances[0]
    func = tokens.spi_function
    port = tokens.pins[0][0] if tokens.pins else None
    pin = tokens.pins[0][1] if tokens.pins else None
    return ParsedIntent(
        peripheral="spi",
        configuration=SPIConfig(
            instance=instance,
            function=func,
            port=port,
            pin=pin,
        ),
        clock_enable=tokens.clock_enable,
    )


def _build_i2c_intent(tokens: LexerTokens) -> ParsedIntent:
    instance = tokens.i2c_instances[0]
    func = tokens.i2c_function
    port = tokens.pins[0][0] if tokens.pins else None
    pin = tokens.pins[0][1] if tokens.pins else None
    return ParsedIntent(
        peripheral="i2c",
        configuration=I2CConfig(
            instance=instance,
            function=func,
            port=port,
            pin=pin,
        ),
        clock_enable=tokens.clock_enable,
    )


def _build_i2c_dual(tokens: LexerTokens) -> List[ParsedIntent]:
    """Handle I2C prompts referencing two pins (SCL + SDA)."""
    instance = tokens.i2c_instances[0]
    intents = []
    for idx, (port, pin) in enumerate(tokens.pins[:2]):
        # First pin → scl, second pin → sda (convention)
        func = "scl" if idx == 0 else "sda"
        intents.append(
            ParsedIntent(
                peripheral="i2c",
                configuration=I2CConfig(
                    instance=instance,
                    function=func,
                    port=port,
                    pin=pin,
                ),
                clock_enable=tokens.clock_enable,
            )
        )
    return intents


def _build_exti_intent(tokens: LexerTokens) -> ParsedIntent:
    line = tokens.exti_lines[0]
    port = tokens.pins[0][0] if tokens.pins else None
    pin = tokens.pins[0][1] if tokens.pins else None
    return ParsedIntent(
        peripheral="exti",
        configuration=EXTIConfig(
            line=line,
            trigger=tokens.exti_trigger,
            port=port,
            pin=pin,
        ),
        clock_enable=tokens.clock_enable,
    )
