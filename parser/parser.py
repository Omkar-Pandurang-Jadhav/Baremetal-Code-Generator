

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

# ✅ NEW IMPORT (LLM NORMALIZER)
from parser.normalizer import normalize_prompt
import os
print("📂 PARSER FILE:", os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(prompt: str) -> ParsedIntent:
    """
    Parse a natural-language prompt into a single ParsedIntent.
    """

    # 🔥 STEP 1: Normalize using LLM
    print("before")
    prompt = normalize_prompt(prompt)
    print("afdter")

    tokens = tokenize(prompt)
    intent = _build_intent(tokens)
    return validate(intent)


def parse_multi(prompt: str) -> MultiParsedIntent:
    """
    Parse multi-command prompts into multiple intents.
    """

    # 🔥 STEP 1: Normalize using LLM
    print("before")
    prompt = normalize_prompt(prompt)
    print("afdter")
    print("afdter")

    segments = split_prompt(prompt)
    segments = propagate_context(segments)

    intents = []

    for segment in segments:
        try:
            tokens = tokenize(segment)
            built_intents = _build_intents(tokens)

            for intent in built_intents:
                intents.append(validate(intent))

        except Exception:
            continue

    if not intents:
        raise ValueError("No valid configuration detected.")

    return MultiParsedIntent(intents=intents)


# ---------------------------------------------------------------------------
# Intent construction
# ---------------------------------------------------------------------------

def _build_intents(tokens: LexerTokens) -> List[ParsedIntent]:
    """Build one or more intents from tokens."""
    if tokens.i2c_instances and len(tokens.pins) == 2:
        return _build_i2c_dual(tokens)

    return [_build_intent(tokens)]


def _build_intent(tokens: LexerTokens) -> ParsedIntent:
    """Build a single ParsedIntent."""

    if tokens.usart_instances:
        return _build_usart_intent(tokens)
    if tokens.timer_instances:
        return _build_timer_intent(tokens)
    if tokens.adc_instances:
        return _build_adc_intent(tokens)
    if tokens.spi_instances:
        return _build_spi_intents(tokens)
    if tokens.i2c_instances:
        return _build_i2c_intent(tokens)
    if tokens.exti_lines:
        return _build_exti_intent(tokens)
    if tokens.pins or tokens.gpio_ports:
        return _build_gpio_intent(tokens)

    raise ValueError("Could not determine peripheral from prompt.")


# ---------------------------------------------------------------------------
# Peripheral builders
# ---------------------------------------------------------------------------

def _build_gpio_intent(tokens: LexerTokens) -> ParsedIntent:
    if not tokens.pins:
        raise ValueError("GPIO requires pin")

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

    port = None
    pin = None

    key = f"usart{instance}"
    valid_pins = hw.AF_PIN_MAP.get((key, func), set())

    for p, pn in tokens.pins:
        if (p, pn) in valid_pins:
            port, pin = p, pn
            break

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
                port, pin = p, pn
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
                port, pin, channel = p, pn, ch
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


def _build_spi_intents(tokens: LexerTokens) -> List[ParsedIntent]:
    """
    Build multiple SPI intents (MOSI, MISO, SCK, NSS).
    """

    instance = tokens.spi_instances[0]
    key = f"spi{instance}"

    intents = []

    # All possible SPI functions
    spi_functions = ["mosi", "miso", "sck", "nss"]

    # Track used pins
    used_pins = set()

    for func in spi_functions:
        valid_pins = hw.AF_PIN_MAP.get((key, func), set())

        for p, pn in tokens.pins:
            if (p, pn) in valid_pins and (p, pn) not in used_pins:
                intents.append(
                    ParsedIntent(
                        peripheral="spi",
                        configuration=SPIConfig(
                            instance=instance,
                            function=func,
                            port=p,
                            pin=pn,
                        ),
                        clock_enable=tokens.clock_enable,
                    )
                )
                used_pins.add((p, pn))
                break

    # Fallback (if nothing matched)
    if not intents and tokens.pins:
        p, pn = tokens.pins[0]
        intents.append(
            ParsedIntent(
                peripheral="spi",
                configuration=SPIConfig(
                    instance=instance,
                    function=None,
                    port=p,
                    pin=pn,
                ),
                clock_enable=tokens.clock_enable,
            )
        )

    return intents
def _build_i2c_intent(tokens: LexerTokens) -> ParsedIntent:
    instance = tokens.i2c_instances[0]
    func = tokens.i2c_function

    port = None
    pin = None

    key = f"i2c{instance}"
    valid_pins = hw.AF_PIN_MAP.get((key, func), set())

    for p, pn in tokens.pins:
        if (p, pn) in valid_pins:
            port, pin = p, pn
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
            port, pin = p, pn
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