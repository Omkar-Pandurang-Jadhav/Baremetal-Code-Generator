"""
Tests for the STM32 prompt parser module.

Covers lexer token extraction, syntax parsing, semantic validation,
and end-to-end prompt→JSON conversion for all supported peripherals.
"""

from __future__ import annotations

import json

import pydantic
import pytest

from parser import (
    ValidationError,
    parse,
    parse_multi,
    tokenize,
)


# =========================================================================
# Lexer tests
# =========================================================================

class TestLexer:
    """Verify lexical token extraction from natural-language prompts."""

    def test_extract_pin(self):
        tokens = tokenize("Configure PA5 as output")
        assert ("A", 5) in tokens.pins

    def test_extract_multiple_pins(self):
        tokens = tokenize("Enable I2C1 on PB6 and PB7")
        assert ("B", 6) in tokens.pins
        assert ("B", 7) in tokens.pins

    def test_extract_speed(self):
        tokens = tokenize("PA5 output push-pull 50 MHz")
        assert 50 in tokens.speeds_mhz

    def test_extract_gpio_port(self):
        tokens = tokenize("enable clock for GPIOA")
        assert "A" in tokens.gpio_ports

    def test_extract_usart_instance(self):
        tokens = tokenize("Enable USART1 TX on PA9")
        assert 1 in tokens.usart_instances
        assert tokens.usart_function == "tx"

    def test_extract_timer_instance_and_channel(self):
        tokens = tokenize("Configure TIM2 channel 1 PWM output")
        assert 2 in tokens.timer_instances
        assert 1 in tokens.timer_channels
        assert tokens.timer_mode == "pwm"

    def test_extract_adc_instance(self):
        tokens = tokenize("Setup ADC1 on PA0")
        assert 1 in tokens.adc_instances

    def test_extract_spi_instance(self):
        tokens = tokenize("Configure SPI1 MOSI on PA7")
        assert 1 in tokens.spi_instances
        assert tokens.spi_function == "mosi"

    def test_extract_i2c_instance(self):
        tokens = tokenize("Enable I2C1 on PB6 and PB7")
        assert 1 in tokens.i2c_instances

    def test_extract_exti_line(self):
        tokens = tokenize("Configure EXTI line 5 rising edge")
        assert 5 in tokens.exti_lines
        assert tokens.exti_trigger == "rising"

    def test_clock_enable_flag(self):
        tokens = tokenize("enable the clock for GPIOA")
        assert tokens.clock_enable is True

    def test_output_mode_detection(self):
        tokens = tokenize("PA5 as GPIO output push-pull 50MHz")
        assert tokens.gpio_mode == "output"
        assert tokens.output_type == "push_pull"

    def test_input_mode_detection(self):
        tokens = tokenize("PA0 as input pull-up")
        assert tokens.gpio_mode == "input"
        assert tokens.input_type == "pull_up"

    def test_analog_mode_detection(self):
        tokens = tokenize("PA0 analog input")
        assert tokens.gpio_mode == "analog"

    def test_speed_without_space(self):
        tokens = tokenize("PA5 output push-pull 50MHz")
        assert 50 in tokens.speeds_mhz


# =========================================================================
# Parser tests — end-to-end prompt → structured JSON
# =========================================================================

class TestParser:
    """Verify full parse pipeline from prompt to validated intent."""

    def test_gpio_output_push_pull(self):
        result = parse(
            "Configure PA5 as GPIO output push-pull at 50 MHz "
            "and enable the clock for GPIOA"
        )
        assert result.mcu == "stm32f103vb"
        assert result.peripheral == "gpio"
        assert result.configuration.port == "A"
        assert result.configuration.pin == 5
        assert result.configuration.mode == "output"
        assert result.configuration.output_type == "push_pull"
        assert result.configuration.speed_mhz == 50
        assert result.clock_enable is True

    def test_usart1_tx(self):
        result = parse("Enable USART1 TX on PA9")
        assert result.peripheral == "usart"
        assert result.configuration.instance == 1
        assert result.configuration.function == "tx"
        assert result.configuration.port == "A"
        assert result.configuration.pin == 9

    def test_timer_pwm(self):
        result = parse("Configure TIM2 channel 1 PWM output")
        assert result.peripheral == "tim"
        assert result.configuration.instance == 2
        assert result.configuration.channel == 1
        assert result.configuration.mode == "pwm"

    def test_adc_on_pin(self):
        result = parse("Setup ADC1 on PA0")
        assert result.peripheral == "adc"
        assert result.configuration.instance == 1
        assert result.configuration.port == "A"
        assert result.configuration.pin == 0
        assert result.configuration.channel == 0  # PA0 = ADC channel 0

    def test_i2c_dual_pins(self):
        result = parse_multi("Enable I2C1 on PB6 and PB7")
        assert len(result.intents) == 2
        scl = result.intents[0]
        sda = result.intents[1]
        assert scl.configuration.function == "scl"
        assert scl.configuration.port == "B"
        assert scl.configuration.pin == 6
        assert sda.configuration.function == "sda"
        assert sda.configuration.port == "B"
        assert sda.configuration.pin == 7

    def test_json_serialization(self):
        result = parse(
            "Configure PA5 as GPIO output push-pull at 50 MHz "
            "and enable the clock for GPIOA"
        )
        data = result.model_dump()
        # Ensure it is JSON-serializable
        json_str = json.dumps(data)
        assert '"mcu": "stm32f103vb"' in json_str
        assert '"peripheral": "gpio"' in json_str

    def test_gpio_defaults_to_output(self):
        """When mode is not explicitly stated, default to output."""
        result = parse("Configure PA5 push-pull 50 MHz")
        assert result.configuration.mode == "output"

    def test_gpio_input_floating(self):
        result = parse("PA3 as input floating")
        assert result.configuration.mode == "input"
        assert result.configuration.input_type == "floating"

    def test_spi_mosi(self):
        result = parse("Configure SPI1 MOSI on PA7")
        assert result.peripheral == "spi"
        assert result.configuration.instance == 1
        assert result.configuration.function == "mosi"
        assert result.configuration.port == "A"
        assert result.configuration.pin == 7

    def test_exti_rising(self):
        result = parse("Configure EXTI line 5 rising edge on PA5")
        assert result.peripheral == "exti"
        assert result.configuration.line == 5
        assert result.configuration.trigger == "rising"


# =========================================================================
# Validation tests — semantic constraints
# =========================================================================

class TestValidation:
    """Verify that invalid configurations are rejected."""

    def test_invalid_gpio_port(self):
        with pytest.raises(ValidationError, match="Invalid GPIO port"):
            parse("Configure PF5 as GPIO output push-pull")

    def test_invalid_pin_number(self):
        with pytest.raises(pydantic.ValidationError):
            # Pin 20 is out of range 0–15 — caught by Pydantic model constraint
            parse("Configure PA20 as GPIO output")

    def test_invalid_speed(self):
        with pytest.raises(pydantic.ValidationError):
            # 25 MHz is not a valid speed — caught by Pydantic Literal constraint
            parse("Configure PA5 as GPIO output push-pull at 25 MHz")

    def test_invalid_usart_pin_mapping(self):
        """USART1 TX must be on PA9, not PA5."""
        with pytest.raises(ValidationError, match="cannot be mapped"):
            parse("Enable USART1 TX on PA5")

    def test_no_peripheral_detected(self):
        with pytest.raises(ValueError, match="Could not determine peripheral"):
            parse("hello world")

    def test_invalid_timer_instance(self):
        """Timer instances beyond 4 should not match the regex."""
        with pytest.raises(ValueError, match="Could not determine peripheral"):
            parse("Configure TIM9 channel 1")

    def test_adc_channel_pin_mismatch(self):
        """ADC channel 0 is PA0, not PA5."""
        # This prompt maps ADC1 to PA5 (which is ADC channel 5).
        result = parse("Setup ADC1 on PA5")
        assert result.configuration.channel == 5

    def test_i2c_invalid_pin(self):
        """I2C1 SCL must be on PB6, not PA0."""
        with pytest.raises(ValidationError, match="cannot be mapped"):
            parse("Enable I2C1 SCL on PA0")


# =========================================================================
# Edge-case tests
# =========================================================================

class TestEdgeCases:
    """Cover unusual or boundary inputs."""

    def test_case_insensitive_pin(self):
        result = parse("Configure pa5 as output push-pull 50mhz")
        assert result.configuration.port == "A"
        assert result.configuration.pin == 5

    def test_multiple_speeds_takes_first(self):
        result = parse("PA5 output push-pull 50MHz 10MHz")
        assert result.configuration.speed_mhz == 50

    def test_gpio_pin_boundary_low(self):
        result = parse("Configure PA0 as output push-pull")
        assert result.configuration.pin == 0

    def test_gpio_pin_boundary_high(self):
        result = parse("Configure PA15 as output push-pull")
        assert result.configuration.pin == 15

    def test_all_valid_ports(self):
        for port_letter in "ABCDE":
            result = parse(f"Configure P{port_letter}0 as output push-pull")
            assert result.configuration.port == port_letter

    def test_usart2_rx(self):
        result = parse("Configure USART2 RX on PA3")
        assert result.configuration.instance == 2
        assert result.configuration.function == "rx"
        assert result.configuration.port == "A"
        assert result.configuration.pin == 3

    def test_timer_without_channel(self):
        result = parse("Configure TIM3")
        assert result.peripheral == "tim"
        assert result.configuration.instance == 3
        assert result.configuration.channel is None

    def test_multi_intent_returns_single(self):
        """parse_multi with a single-intent prompt returns one intent."""
        result = parse_multi("Configure PA5 as output push-pull 50 MHz")
        assert len(result.intents) == 1
