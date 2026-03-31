"""
STM32F103VB hardware constraints derived from RM0008 reference manual
and STM32F103VB datasheet.

This module defines valid configurations, pin mappings, alternate function
assignments, and RCC clock domains for the STM32F103VB medium-density
value-line device.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Set, Tuple

# ---------------------------------------------------------------------------
# MCU identification
# ---------------------------------------------------------------------------
SUPPORTED_MCUS: FrozenSet[str] = frozenset({"stm32f103vb"})

# ---------------------------------------------------------------------------
# GPIO constraints (RM0008 §9)
# ---------------------------------------------------------------------------
VALID_GPIO_PORTS: FrozenSet[str] = frozenset({"A", "B", "C", "D", "E"})

VALID_PIN_RANGE: Tuple[int, int] = (0, 15)

VALID_GPIO_MODES: FrozenSet[str] = frozenset({
    "input",
    "output",
    "alternate_function",
    "analog",
})

VALID_OUTPUT_TYPES: FrozenSet[str] = frozenset({
    "push_pull",
    "open_drain",
})

VALID_INPUT_TYPES: FrozenSet[str] = frozenset({
    "floating",
    "pull_up",
    "pull_down",
})

# RM0008 §9.2.1 — CRL/CRH MODE bits
VALID_SPEEDS_MHZ: FrozenSet[int] = frozenset({2, 10, 50})

# ---------------------------------------------------------------------------
# Supported peripherals
# ---------------------------------------------------------------------------
SUPPORTED_PERIPHERALS: FrozenSet[str] = frozenset({
    "gpio",
    "rcc",
    "usart",
    "tim",
    "adc",
    "spi",
    "i2c",
    "exti",
})

# ---------------------------------------------------------------------------
# RCC clock enable bits (RM0008 §7.3.7 / §7.3.8)
# Maps peripheral name to (bus, bit-name) for documentation traceability.
# ---------------------------------------------------------------------------
RCC_CLOCK_MAP: Dict[str, Tuple[str, str]] = {
    "gpioa": ("apb2", "IOPAEN"),
    "gpiob": ("apb2", "IOPBEN"),
    "gpioc": ("apb2", "IOPCEN"),
    "gpiod": ("apb2", "IOPDEN"),
    "gpioe": ("apb2", "IOPEEN"),
    "usart1": ("apb2", "USART1EN"),
    "usart2": ("apb1", "USART2EN"),
    "usart3": ("apb1", "USART3EN"),
    "tim1": ("apb2", "TIM1EN"),
    "tim2": ("apb1", "TIM2EN"),
    "tim3": ("apb1", "TIM3EN"),
    "tim4": ("apb1", "TIM4EN"),
    "adc1": ("apb2", "ADC1EN"),
    "adc2": ("apb2", "ADC2EN"),
    "spi1": ("apb2", "SPI1EN"),
    "spi2": ("apb1", "SPI2EN"),
    "i2c1": ("apb1", "I2C1EN"),
    "i2c2": ("apb1", "I2C2EN"),
    "afio": ("apb2", "AFIOEN"),
}

# ---------------------------------------------------------------------------
# Alternate-function pin mappings (RM0008 §9.3.8, Table 25)
# Key: (peripheral, function) → set of valid (port, pin) pairs
# ---------------------------------------------------------------------------
AF_PIN_MAP: Dict[Tuple[str, str], Set[Tuple[str, int]]] = {
    # USART1
    ("usart1", "tx"): {("A", 9)},
    ("usart1", "rx"): {("A", 10)},
    # USART2
    ("usart2", "tx"): {("A", 2)},
    ("usart2", "rx"): {("A", 3)},
    # USART3
    ("usart3", "tx"): {("B", 10)},
    ("usart3", "rx"): {("B", 11)},
    # SPI1
    ("spi1", "sck"):  {("A", 5)},
    ("spi1", "miso"): {("A", 6)},
    ("spi1", "mosi"): {("A", 7)},
    ("spi1", "nss"):  {("A", 4)},
    # SPI2
    ("spi2", "sck"):  {("B", 13)},
    ("spi2", "miso"): {("B", 14)},
    ("spi2", "mosi"): {("B", 15)},
    ("spi2", "nss"):  {("B", 12)},
    # I2C1
    ("i2c1", "scl"): {("B", 6)},
    ("i2c1", "sda"): {("B", 7)},
    # I2C2
    ("i2c2", "scl"): {("B", 10)},
    ("i2c2", "sda"): {("B", 11)},
    # TIM1 channels
    ("tim1", "ch1"): {("A", 8)},
    ("tim1", "ch2"): {("A", 9)},
    ("tim1", "ch3"): {("A", 10)},
    ("tim1", "ch4"): {("A", 11)},
    # TIM2 channels
    ("tim2", "ch1"): {("A", 0)},
    ("tim2", "ch2"): {("A", 1)},
    ("tim2", "ch3"): {("A", 2)},
    ("tim2", "ch4"): {("A", 3)},
    # TIM3 channels
    ("tim3", "ch1"): {("A", 6)},
    ("tim3", "ch2"): {("A", 7)},
    ("tim3", "ch3"): {("B", 0)},
    ("tim3", "ch4"): {("B", 1)},
    # TIM4 channels
    ("tim4", "ch1"): {("B", 6)},
    ("tim4", "ch2"): {("B", 7)},
    ("tim4", "ch3"): {("B", 8)},
    ("tim4", "ch4"): {("B", 9)},
}

# ---------------------------------------------------------------------------
# Timer constraints
# ---------------------------------------------------------------------------
VALID_TIMERS: FrozenSet[str] = frozenset({"tim1", "tim2", "tim3", "tim4"})

VALID_TIMER_CHANNELS: FrozenSet[int] = frozenset({1, 2, 3, 4})

VALID_TIMER_MODES: FrozenSet[str] = frozenset({
    "pwm",
    "output_compare",
    "input_capture",
})

# ---------------------------------------------------------------------------
# ADC constraints (RM0008 §11)
# ---------------------------------------------------------------------------
VALID_ADCS: FrozenSet[str] = frozenset({"adc1", "adc2"})

# ADC channel → (port, pin) mapping for external channels
ADC_CHANNEL_PIN_MAP: Dict[int, Tuple[str, int]] = {
    0:  ("A", 0),
    1:  ("A", 1),
    2:  ("A", 2),
    3:  ("A", 3),
    4:  ("A", 4),
    5:  ("A", 5),
    6:  ("A", 6),
    7:  ("A", 7),
    8:  ("B", 0),
    9:  ("B", 1),
    10: ("C", 0),
    11: ("C", 1),
    12: ("C", 2),
    13: ("C", 3),
    14: ("C", 4),
    15: ("C", 5),
}

# ---------------------------------------------------------------------------
# USART constraints
# ---------------------------------------------------------------------------
VALID_USARTS: FrozenSet[str] = frozenset({"usart1", "usart2", "usart3"})

VALID_USART_FUNCTIONS: FrozenSet[str] = frozenset({"tx", "rx"})

# ---------------------------------------------------------------------------
# SPI constraints
# ---------------------------------------------------------------------------
VALID_SPIS: FrozenSet[str] = frozenset({"spi1", "spi2"})

VALID_SPI_FUNCTIONS: FrozenSet[str] = frozenset({"sck", "miso", "mosi", "nss"})

# ---------------------------------------------------------------------------
# I2C constraints
# ---------------------------------------------------------------------------
VALID_I2CS: FrozenSet[str] = frozenset({"i2c1", "i2c2"})

VALID_I2C_FUNCTIONS: FrozenSet[str] = frozenset({"scl", "sda"})

# ---------------------------------------------------------------------------
# EXTI constraints (RM0008 §10.2)
# ---------------------------------------------------------------------------
VALID_EXTI_LINES: FrozenSet[int] = frozenset(range(0, 16))

VALID_EXTI_TRIGGERS: FrozenSet[str] = frozenset({
    "rising",
    "falling",
    "both",
})
