"""
Pydantic models representing the structured JSON output of the prompt parser.

Every downstream component (Context Builder, STM32 LLM, Code Generator)
consumes instances of these models, so changes here must be made carefully.
"""

from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Per-peripheral configuration models
# ---------------------------------------------------------------------------

class GPIOConfig(BaseModel):
    """GPIO pin configuration."""
    port: str = Field(..., description="GPIO port letter (A–E)")
    pin: int = Field(..., ge=0, le=15, description="Pin number 0–15")
    mode: Literal["input", "output", "alternate_function", "analog"]
    output_type: Optional[Literal["push_pull", "open_drain"]] = None
    input_type: Optional[Literal["floating", "pull_up", "pull_down"]] = None
    speed_mhz: Optional[Literal[2, 10, 50]] = None


class USARTConfig(BaseModel):
    """USART peripheral configuration."""
    instance: int = Field(..., ge=1, le=3, description="USART instance (1–3)")
    function: Literal["tx", "rx"]
    port: Optional[str] = None
    pin: Optional[int] = Field(None, ge=0, le=15)
    baud_rate: Optional[int] = None


class TimerConfig(BaseModel):
    """Timer peripheral configuration."""
    instance: int = Field(..., ge=1, le=4, description="Timer instance (1–4)")
    channel: Optional[int] = Field(None, ge=1, le=4)
    mode: Optional[Literal["pwm", "output_compare", "input_capture"]] = None
    port: Optional[str] = None
    pin: Optional[int] = Field(None, ge=0, le=15)


class ADCConfig(BaseModel):
    """ADC peripheral configuration."""
    instance: int = Field(..., ge=1, le=2, description="ADC instance (1–2)")
    channel: Optional[int] = Field(None, ge=0, le=15)
    port: Optional[str] = None
    pin: Optional[int] = Field(None, ge=0, le=15)


class SPIConfig(BaseModel):
    """SPI peripheral configuration."""
    instance: int = Field(..., ge=1, le=2, description="SPI instance (1–2)")
    function: Optional[Literal["sck", "miso", "mosi", "nss"]] = None
    port: Optional[str] = None
    pin: Optional[int] = Field(None, ge=0, le=15)


class I2CConfig(BaseModel):
    """I2C peripheral configuration."""
    instance: int = Field(..., ge=1, le=2, description="I2C instance (1–2)")
    function: Optional[Literal["scl", "sda"]] = None
    port: Optional[str] = None
    pin: Optional[int] = Field(None, ge=0, le=15)


class EXTIConfig(BaseModel):
    """External interrupt configuration."""
    line: int = Field(..., ge=0, le=15, description="EXTI line (0–15)")
    trigger: Optional[Literal["rising", "falling", "both"]] = None
    port: Optional[str] = None
    pin: Optional[int] = Field(None, ge=0, le=15)


class RCCConfig(BaseModel):
    """RCC clock configuration."""
    peripheral: str = Field(..., description="Peripheral whose clock to enable")
    enable: bool = True


# Union of all configuration types
ConfigurationType = Union[
    GPIOConfig,
    USARTConfig,
    TimerConfig,
    ADCConfig,
    SPIConfig,
    I2CConfig,
    EXTIConfig,
    RCCConfig,
]


# ---------------------------------------------------------------------------
# Top-level parsed result
# ---------------------------------------------------------------------------

class ParsedIntent(BaseModel):
    """Top-level structured output produced by the parser pipeline."""
    mcu: str = Field(default="stm32f103vb", description="Target MCU")
    peripheral: str = Field(..., description="Primary peripheral type")
    configuration: ConfigurationType = Field(
        ..., description="Peripheral-specific configuration"
    )
    clock_enable: bool = Field(
        default=False,
        description="Whether RCC clock enabling was requested",
    )


class MultiParsedIntent(BaseModel):
    """Container for prompts that yield multiple configuration intents."""
    intents: List[ParsedIntent]
