"""Schema definitions for the STM32F103VB prompt parser.

Defines the data models used throughout the parser pipeline
for representing hardware configuration intents.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Token:
    """Represents a lexer token extracted from user input."""
    type: str       # e.g., 'PIN', 'PERIPHERAL', 'FUNCTION', 'MODE', 'SPEED', 'ACTION'
    value: str      # e.g., 'PA5', 'USART1', 'TX', 'push-pull', '50MHz', 'configure'
    position: int   # character position in original text


@dataclass
class Intent:
    """Represents a single hardware configuration intent."""
    peripheral: str                     # e.g., 'GPIO', 'USART1', 'SPI1', 'ADC1'
    pin: str                            # e.g., 'PA5', 'PA9'
    function: Optional[str] = None      # e.g., 'TX', 'RX', 'MOSI', 'MISO'
    mode: Optional[str] = None          # e.g., 'output', 'input', 'alternate'
    output_type: Optional[str] = None   # e.g., 'push-pull', 'open-drain'
    speed: Optional[str] = None         # e.g., '2MHz', '10MHz', '50MHz'
    pull: Optional[str] = None          # e.g., 'pull-up', 'pull-down', 'floating'

    def summary(self) -> str:
        """Return a short summary string like 'GPIO PA5' or 'USART1 TX PA9'."""
        parts = [self.peripheral]
        if self.function:
            parts.append(self.function)
        parts.append(self.pin)
        return " ".join(parts)


@dataclass
class ParseResult:
    """Holds the complete result of parsing a user prompt."""
    intents: List[Intent] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summaries(self) -> List[str]:
        """Return summary strings for all intents."""
        return [intent.summary() for intent in self.intents]
