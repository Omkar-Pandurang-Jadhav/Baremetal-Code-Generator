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
from .prompt_splitter import split_prompt
from .context_resolver import propagate_context

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

    segments = split_prompt(prompt)

    segments = propagate_context(segments)

    intents = []

    for segment in segments:
        try:
            intent = parse(segment)
            intents.append(intent)
        except Exception:
            continue

    if not intents:
        raise ValueError("No valid configuration detected.")

    return MultiParsedIntent(intents=intents)


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
        raise ValueError("GPIO configuration requires a pin (e.g. PA5).")

    # Prefer pins not associated with alternate-function peripherals
    port = None
    pin = None

    for p, pn in tokens.pins:
        port = p
        pin = pn
        break

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
    """
    Build USART configuration intent.

    Improves pin selection by matching pins against valid alternate
    function mappings instead of always choosing the first pin.
    """

    instance = tokens.usart_instances[0]
    func = tokens.usart_function or "tx"

    port = None
    pin = None

    key = f"usart{instance}"

    # Look up valid alternate function pins from hardware rules
    valid_pins = hw.AF_PIN_MAP.get((key, func), set())

    # Try to find a matching pin in the extracted tokens
    for p, pn in tokens.pins:
        if (p, pn) in valid_pins:
            port = p
            pin = pn
            break

    # Fallback if no valid mapping found
    if port is None and tokens.pins:
        port, pin = tokens.pins[0]

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

    port = None
    pin = None

    if channel:
        key = f"tim{instance}"
        ch_key = f"ch{channel}"
        valid_pins = hw.AF_PIN_MAP.get((key, ch_key), set())

        for p, pn in tokens.pins:
            if (p, pn) in valid_pins:
                port = p
                pin = pn
                break

    if port is None and tokens.pins:
        port, pin = tokens.pins[0]

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

    port = None
    pin = None
    channel = None

    for p, pn in tokens.pins:
        for ch, (hp, hpin) in hw.ADC_CHANNEL_PIN_MAP.items():
            if p == hp and pn == hpin:
                port = p
                pin = pn
                channel = ch
                break
        if port:
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

    port = None
    pin = None

    key = f"spi{instance}"
    valid_pins = hw.AF_PIN_MAP.get((key, func), set())

    for p, pn in tokens.pins:
        if (p, pn) in valid_pins:
            port = p
            pin = pn
            break

    if port is None and tokens.pins:
        port, pin = tokens.pins[0]

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

    port = None
    pin = None

    key = f"i2c{instance}"
    valid_pins = hw.AF_PIN_MAP.get((key, func), set())

    for p, pn in tokens.pins:
        if (p, pn) in valid_pins:
            port = p
            pin = pn
            break

    if port is None and tokens.pins:
        port, pin = tokens.pins[0]

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
    instance = tokens.i2c_instances[0]
    intents = []

    key = f"i2c{instance}"

    scl_pins = hw.AF_PIN_MAP.get((key, "scl"), set())
    sda_pins = hw.AF_PIN_MAP.get((key, "sda"), set())

    scl = None
    sda = None

    for p, pn in tokens.pins:
        if (p, pn) in scl_pins:
            scl = (p, pn)
        elif (p, pn) in sda_pins:
            sda = (p, pn)

    if scl:
        intents.append(
            ParsedIntent(
                peripheral="i2c",
                configuration=I2CConfig(
                    instance=instance,
                    function="scl",
                    port=scl[0],
                    pin=scl[1],
                ),
                clock_enable=tokens.clock_enable,
            )
        )

    if sda:
        intents.append(
            ParsedIntent(
                peripheral="i2c",
                configuration=I2CConfig(
                    instance=instance,
                    function="sda",
                    port=sda[0],
                    pin=sda[1],
                ),
                clock_enable=tokens.clock_enable,
            )
        )

    return intents


def _build_exti_intent(tokens: LexerTokens) -> ParsedIntent:
    line = tokens.exti_lines[0]

    port = None
    pin = None

    for p, pn in tokens.pins:
        if pn == line:
            port = p
            pin = pn
            break

    if port is None and tokens.pins:
        port, pin = tokens.pins[0]

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
