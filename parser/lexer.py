"""
Lexical extraction layer for the STM32 prompt parser.

Extracts raw tokens (peripheral names, GPIO ports/pins, speeds, modes, etc.)
from a natural-language configuration request.  The output is a flat
dictionary of extracted token lists that the syntax parser consumes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Compiled regex patterns — compiled once at module load time
# ---------------------------------------------------------------------------

# GPIO pin reference: PA5, PB12, PF5, etc.  Accept any letter so the
# validator can report an "invalid port" error rather than silently ignoring.
_PIN_RE = re.compile(
    r"\bP([A-Z])(\d{1,2})\b",
    re.IGNORECASE,
)

# Speed: "50 MHz", "50MHz", "10mhz", "2 mhz"
_SPEED_RE = re.compile(
    r"\b(\d{1,2})\s*MHz\b",
    re.IGNORECASE,
)

# USART instance: USART1, USART2, USART3
_USART_RE = re.compile(
    r"\bUSART\s*([1-3])\b",
    re.IGNORECASE,
)

# Timer instance: TIM1–TIM4
_TIMER_RE = re.compile(
    r"\bTIM\s*([1-4])\b",
    re.IGNORECASE,
)

# Timer channel: "channel 1", "ch1", "CH 2"
_TIMER_CHANNEL_RE = re.compile(
    r"\b(?:channel|ch)\s*([1-4])\b",
    re.IGNORECASE,
)

# ADC instance: ADC1, ADC2
_ADC_RE = re.compile(
    r"\bADC\s*([1-2])\b",
    re.IGNORECASE,
)

# SPI instance: SPI1, SPI2
_SPI_RE = re.compile(
    r"\bSPI\s*([1-2])\b",
    re.IGNORECASE,
)

# I2C instance: I2C1, I2C2
_I2C_RE = re.compile(
    r"\bI2C\s*([1-2])\b",
    re.IGNORECASE,
)

# EXTI line: "EXTI line 5", "EXTI5"
_EXTI_RE = re.compile(
    r"\bEXTI\s*(?:line\s*)?(\d{1,2})\b",
    re.IGNORECASE,
)

# GPIO port reference without pin: "GPIOA", "GPIOB"
_GPIO_PORT_RE = re.compile(
    r"\bGPIO([A-E])\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Keyword sets for mode / type classification
# ---------------------------------------------------------------------------

_OUTPUT_KEYWORDS = {"output"}
_INPUT_KEYWORDS = {"input"}
_ANALOG_KEYWORDS = {"analog"}
_AF_KEYWORDS = {"alternate", "alternate_function", "af"}

_PUSH_PULL_KEYWORDS = {"push-pull", "push_pull", "pushpull", "pp"}
_OPEN_DRAIN_KEYWORDS = {"open-drain", "open_drain", "opendrain", "od"}

_FLOATING_KEYWORDS = {"floating"}
_PULL_UP_KEYWORDS = {"pull-up", "pull_up", "pullup"}
_PULL_DOWN_KEYWORDS = {"pull-down", "pull_down", "pulldown"}

_TX_KEYWORDS = {"tx", "transmit"}
_RX_KEYWORDS = {"rx", "receive"}

_PWM_KEYWORDS = {"pwm"}
_OUTPUT_COMPARE_KEYWORDS = {"output_compare", "output compare", "oc"}
_INPUT_CAPTURE_KEYWORDS = {"input_capture", "input capture", "ic"}

_SCK_KEYWORDS = {"sck", "clock"}
_MISO_KEYWORDS = {"miso"}
_MOSI_KEYWORDS = {"mosi"}
_NSS_KEYWORDS = {"nss", "cs", "chip select"}

_SCL_KEYWORDS = {"scl"}
_SDA_KEYWORDS = {"sda"}

_RISING_KEYWORDS = {"rising"}
_FALLING_KEYWORDS = {"falling"}
_BOTH_EDGE_KEYWORDS = {"both", "both edges"}

_CLOCK_ENABLE_KEYWORDS = {"enable the clock", "clock enable", "enable clock",
                          "rcc enable", "enable rcc"}

_INTERRUPT_KEYWORDS = {"interrupt", "irq", "exti"}


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------

@dataclass
class LexerTokens:
    """Container for all tokens extracted from the input prompt."""

    # GPIO-related
    pins: List[Tuple[str, int]] = field(default_factory=list)
    gpio_ports: List[str] = field(default_factory=list)
    speeds_mhz: List[int] = field(default_factory=list)
    gpio_mode: Optional[str] = None          # input / output / alternate_function / analog
    output_type: Optional[str] = None        # push_pull / open_drain
    input_type: Optional[str] = None         # floating / pull_up / pull_down

    # Peripheral instances
    usart_instances: List[int] = field(default_factory=list)
    timer_instances: List[int] = field(default_factory=list)
    timer_channels: List[int] = field(default_factory=list)
    adc_instances: List[int] = field(default_factory=list)
    spi_instances: List[int] = field(default_factory=list)
    i2c_instances: List[int] = field(default_factory=list)
    exti_lines: List[int] = field(default_factory=list)

    # Function-level tokens
    usart_function: Optional[str] = None     # tx / rx
    spi_function: Optional[str] = None       # sck / miso / mosi / nss
    i2c_function: Optional[str] = None       # scl / sda
    timer_mode: Optional[str] = None         # pwm / output_compare / input_capture
    exti_trigger: Optional[str] = None       # rising / falling / both

    # Flags
    clock_enable: bool = False
    interrupt_requested: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tokenize(prompt: str) -> LexerTokens:
    """Extract hardware tokens from a natural-language *prompt*."""
    tokens = LexerTokens()
    lower = prompt.lower()

    # --- regex-based extraction -------------------------------------------
    for m in _PIN_RE.finditer(prompt):
        port = m.group(1).upper()
        pin = int(m.group(2))
        tokens.pins.append((port, pin))

    for m in _GPIO_PORT_RE.finditer(prompt):
        tokens.gpio_ports.append(m.group(1).upper())

    for m in _SPEED_RE.finditer(prompt):
        tokens.speeds_mhz.append(int(m.group(1)))

    for m in _USART_RE.finditer(prompt):
        tokens.usart_instances.append(int(m.group(1)))

    for m in _TIMER_RE.finditer(prompt):
        tokens.timer_instances.append(int(m.group(1)))

    for m in _TIMER_CHANNEL_RE.finditer(prompt):
        tokens.timer_channels.append(int(m.group(1)))

    for m in _ADC_RE.finditer(prompt):
        tokens.adc_instances.append(int(m.group(1)))

    for m in _SPI_RE.finditer(prompt):
        tokens.spi_instances.append(int(m.group(1)))

    for m in _I2C_RE.finditer(prompt):
        tokens.i2c_instances.append(int(m.group(1)))

    for m in _EXTI_RE.finditer(prompt):
        tokens.exti_lines.append(int(m.group(1)))

    # --- keyword-based extraction -----------------------------------------

    # GPIO mode
    if _any_keyword(lower, _ANALOG_KEYWORDS):
        tokens.gpio_mode = "analog"
    elif _any_keyword(lower, _AF_KEYWORDS):
        tokens.gpio_mode = "alternate_function"
    elif _any_keyword(lower, _OUTPUT_KEYWORDS):
        tokens.gpio_mode = "output"
    elif _any_keyword(lower, _INPUT_KEYWORDS):
        tokens.gpio_mode = "input"

    # Output type
    if _any_keyword(lower, _PUSH_PULL_KEYWORDS):
        tokens.output_type = "push_pull"
    elif _any_keyword(lower, _OPEN_DRAIN_KEYWORDS):
        tokens.output_type = "open_drain"

    # Input type
    if _any_keyword(lower, _PULL_UP_KEYWORDS):
        tokens.input_type = "pull_up"
    elif _any_keyword(lower, _PULL_DOWN_KEYWORDS):
        tokens.input_type = "pull_down"
    elif _any_keyword(lower, _FLOATING_KEYWORDS):
        tokens.input_type = "floating"

    # USART function
    if _any_keyword(lower, _TX_KEYWORDS):
        tokens.usart_function = "tx"
    if _any_keyword(lower, _RX_KEYWORDS):
        tokens.usart_function = "rx"  # last-write-wins for single function

    # Timer mode
    if _any_keyword(lower, _PWM_KEYWORDS):
        tokens.timer_mode = "pwm"
    elif _any_keyword(lower, _OUTPUT_COMPARE_KEYWORDS):
        tokens.timer_mode = "output_compare"
    elif _any_keyword(lower, _INPUT_CAPTURE_KEYWORDS):
        tokens.timer_mode = "input_capture"

    # SPI function
    if _any_keyword(lower, _MOSI_KEYWORDS):
        tokens.spi_function = "mosi"
    elif _any_keyword(lower, _MISO_KEYWORDS):
        tokens.spi_function = "miso"
    elif _any_keyword(lower, _SCK_KEYWORDS):
        tokens.spi_function = "sck"
    elif _any_keyword(lower, _NSS_KEYWORDS):
        tokens.spi_function = "nss"

    # I2C function
    if _any_keyword(lower, _SCL_KEYWORDS):
        tokens.i2c_function = "scl"
    elif _any_keyword(lower, _SDA_KEYWORDS):
        tokens.i2c_function = "sda"

    # EXTI trigger
    if _any_keyword(lower, _BOTH_EDGE_KEYWORDS):
        tokens.exti_trigger = "both"
    elif _any_keyword(lower, _RISING_KEYWORDS):
        tokens.exti_trigger = "rising"
    elif _any_keyword(lower, _FALLING_KEYWORDS):
        tokens.exti_trigger = "falling"

    # Clock enable flag
    if _any_keyword(lower, _CLOCK_ENABLE_KEYWORDS):
        tokens.clock_enable = True

    # Interrupt
    if _any_keyword(lower, _INTERRUPT_KEYWORDS):
        tokens.interrupt_requested = True

    return tokens


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _any_keyword(text: str, keywords: Set[str]) -> bool:
    """Return *True* if any keyword from *keywords* appears in *text*."""
    return any(kw in text for kw in keywords)
