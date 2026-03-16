"""
STM32 Prompt Parser — public API.

Converts natural-language STM32 configuration requests into validated
structured JSON for the STM32F103VB microcontroller.

Usage
-----
>>> from parser import parse
>>> result = parse("Configure PA5 as GPIO output push-pull at 50 MHz and enable the clock for GPIOA")
>>> result.model_dump()
{'mcu': 'stm32f103vb', 'peripheral': 'gpio', ...}
"""

from .lexer import LexerTokens, tokenize
from .parser import parse, parse_multi
from .schema import (
    ADCConfig,
    ConfigurationType,
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

__all__ = [
    # Main entry points
    "parse",
    "parse_multi",
    "tokenize",
    "validate",
    # Schema models
    "ParsedIntent",
    "MultiParsedIntent",
    "ConfigurationType",
    "GPIOConfig",
    "USARTConfig",
    "TimerConfig",
    "ADCConfig",
    "SPIConfig",
    "I2CConfig",
    "EXTIConfig",
    "RCCConfig",
    # Lexer
    "LexerTokens",
    # Errors
    "ValidationError",
]
