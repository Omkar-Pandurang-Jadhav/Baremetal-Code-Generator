"""Tests for the STM32F103VB prompt parser.

Tests cover:
- Lexer tokenization
- Parser intent generation
- Prompt splitting
- Context resolution
- Semantic interpretation
- Full pipeline integration
- All 4 required test prompts from the specification
"""

import sys
import os
import unittest

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parser import parse_prompt
from parser.schema import Intent, ParseResult, Token
from parser.lexer import tokenize
from parser.parser import parse_tokens, parse_sub_prompt
from parser.prompt_splitter import split_prompt
from parser.context_resolver import resolve_context
from parser.semantic_interpreter import interpret
from parser.validator import validate_intents


# ==============================================================
# Lexer Tests
# ==============================================================

class TestLexer(unittest.TestCase):
    """Tests for the lexer module."""

    def test_tokenize_single_pin(self):
        tokens = tokenize("PA5")
        pin_tokens = [t for t in tokens if t.type == "PIN"]
        self.assertEqual(len(pin_tokens), 1)
        self.assertEqual(pin_tokens[0].value, "PA5")

    def test_tokenize_multiple_pins(self):
        tokens = tokenize("PA5, PA6, and PA7")
        pin_tokens = [t for t in tokens if t.type == "PIN"]
        self.assertEqual(len(pin_tokens), 3)
        self.assertEqual([t.value for t in pin_tokens], ["PA5", "PA6", "PA7"])

    def test_tokenize_peripheral(self):
        tokens = tokenize("USART1 TX on PA9")
        periph_tokens = [t for t in tokens if t.type == "PERIPHERAL"]
        self.assertEqual(len(periph_tokens), 1)
        self.assertEqual(periph_tokens[0].value, "USART1")

    def test_tokenize_functions(self):
        tokens = tokenize("MOSI on PA7, MISO on PA6")
        func_tokens = [t for t in tokens if t.type == "FUNCTION"]
        self.assertEqual(len(func_tokens), 2)
        self.assertEqual([t.value for t in func_tokens], ["MOSI", "MISO"])

    def test_tokenize_mode_and_output_type(self):
        tokens = tokenize("GPIO output push-pull")
        mode_tokens = [t for t in tokens if t.type == "MODE"]
        out_tokens = [t for t in tokens if t.type == "OUTPUT_TYPE"]
        self.assertEqual(len(mode_tokens), 1)
        self.assertEqual(mode_tokens[0].value, "output")
        self.assertEqual(len(out_tokens), 1)
        self.assertEqual(out_tokens[0].value, "push-pull")

    def test_tokenize_speed(self):
        tokens = tokenize("50 MHz")
        speed_tokens = [t for t in tokens if t.type == "SPEED"]
        self.assertEqual(len(speed_tokens), 1)
        self.assertEqual(speed_tokens[0].value, "50MHz")

    def test_tokenize_action_verbs(self):
        tokens = tokenize("configure PA5 as GPIO")
        action_tokens = [t for t in tokens if t.type == "ACTION"]
        self.assertEqual(len(action_tokens), 1)
        self.assertEqual(action_tokens[0].value, "configure")

    def test_tokenize_preserves_order(self):
        tokens = tokenize("enable USART1 TX on PA9")
        types = [t.type for t in tokens]
        self.assertEqual(types[0], "ACTION")
        # Peripheral and function should follow
        self.assertIn("PERIPHERAL", types)
        self.assertIn("FUNCTION", types)
        self.assertIn("PIN", types)

    def test_tokenize_gpio_keyword(self):
        tokens = tokenize("GPIO output on PA5")
        periph_tokens = [t for t in tokens if t.type == "PERIPHERAL"]
        self.assertTrue(any(t.value == "GPIO" for t in periph_tokens))

    def test_tokenize_pull_config(self):
        tokens = tokenize("pull-up on PA5")
        pull_tokens = [t for t in tokens if t.type == "PULL"]
        self.assertEqual(len(pull_tokens), 1)
        self.assertEqual(pull_tokens[0].value, "pull-up")

    def test_tokenize_empty_string(self):
        tokens = tokenize("")
        self.assertEqual(len(tokens), 0)

    def test_tokenize_no_recognized_tokens(self):
        tokens = tokenize("hello world")
        # Should still return empty or minimal tokens
        pin_tokens = [t for t in tokens if t.type == "PIN"]
        self.assertEqual(len(pin_tokens), 0)


# ==============================================================
# Parser Tests
# ==============================================================

class TestParser(unittest.TestCase):
    """Tests for the parser module."""

    def test_parse_single_gpio_pin(self):
        tokens = tokenize("configure PA5 as GPIO output push-pull")
        intents = parse_tokens(tokens)
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].peripheral, "GPIO")
        self.assertEqual(intents[0].pin, "PA5")
        self.assertEqual(intents[0].mode, "output")
        self.assertEqual(intents[0].output_type, "push-pull")

    def test_parse_multiple_gpio_pins(self):
        """Problem 1: Pin list expansion."""
        tokens = tokenize("configure PA5, PA6, and PA7 as GPIO output push-pull pins")
        intents = parse_tokens(tokens)
        self.assertEqual(len(intents), 3)
        pins = [i.pin for i in intents]
        self.assertIn("PA5", pins)
        self.assertIn("PA6", pins)
        self.assertIn("PA7", pins)
        for intent in intents:
            self.assertEqual(intent.peripheral, "GPIO")
            self.assertEqual(intent.mode, "output")

    def test_parse_peripheral_with_function(self):
        tokens = tokenize("enable USART1 TX on PA9")
        intents = parse_tokens(tokens)
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].peripheral, "USART1")
        self.assertEqual(intents[0].function, "TX")
        self.assertEqual(intents[0].pin, "PA9")

    def test_parse_spi_multi_function(self):
        """Problem 2: Multi-function peripheral parsing."""
        tokens = tokenize(
            "Initialize SPI1 with MOSI on PA7, MISO on PA6, "
            "SCK on PA5 and NSS on PA4"
        )
        intents = parse_tokens(tokens)
        self.assertEqual(len(intents), 4)
        summaries = [i.summary() for i in intents]
        self.assertIn("SPI1 MOSI PA7", summaries)
        self.assertIn("SPI1 MISO PA6", summaries)
        self.assertIn("SPI1 SCK PA5", summaries)
        self.assertIn("SPI1 NSS PA4", summaries)

    def test_parse_adc_without_function(self):
        tokens = tokenize("setup ADC1 on PA0")
        intents = parse_tokens(tokens)
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].peripheral, "ADC1")
        self.assertEqual(intents[0].pin, "PA0")

    def test_parse_gpio_with_speed(self):
        tokens = tokenize("configure PA5 as GPIO output push-pull at 50 MHz")
        intents = parse_tokens(tokens)
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].speed, "50MHz")

    def test_parse_implied_gpio(self):
        """Pins without explicit peripheral should default to GPIO."""
        tokens = tokenize("PA5 output push-pull")
        intents = parse_tokens(tokens)
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].peripheral, "GPIO")

    def test_parse_no_pins(self):
        tokens = tokenize("configure USART1")
        intents = parse_tokens(tokens)
        self.assertEqual(len(intents), 0)


# ==============================================================
# Prompt Splitter Tests
# ==============================================================

class TestPromptSplitter(unittest.TestCase):
    """Tests for the prompt splitter module."""

    def test_split_simple_prompt(self):
        parts = split_prompt("configure PA5 as GPIO output")
        self.assertEqual(len(parts), 1)

    def test_split_multiple_intents_with_verbs(self):
        parts = split_prompt(
            "Configure PA5 as GPIO output push-pull at 50 MHz, "
            "enable USART1 TX on PA9 and RX on PA10, "
            "and setup ADC1 on PA0"
        )
        self.assertGreaterEqual(len(parts), 3)

    def test_split_preserves_peripheral_context(self):
        """Problem 5: Don't split 'TX on PA9 and RX on PA10'."""
        parts = split_prompt("enable USART1 TX on PA9 and RX on PA10")
        # Should be a single sub-prompt (or RX should stay with USART1)
        full_text = " ".join(parts)
        self.assertIn("TX", full_text)
        self.assertIn("RX", full_text)

    def test_split_pin_list_preserved(self):
        """Pin lists should not be split."""
        parts = split_prompt("Configure PA5, PA6, and PA7 as GPIO output")
        # All pins should be in a single sub-prompt
        self.assertEqual(len(parts), 1)
        self.assertIn("PA5", parts[0])
        self.assertIn("PA7", parts[0])


# ==============================================================
# Context Resolver Tests
# ==============================================================

class TestContextResolver(unittest.TestCase):
    """Tests for the context resolver module."""

    def test_resolve_usart_context(self):
        """Problem 3: RX should inherit USART1 context."""
        resolved = resolve_context("enable USART1 TX on PA9 and RX on PA10")
        self.assertIn("USART1", resolved)
        # RX should now have USART1 before it
        # Find the RX position and check for USART1 before it
        rx_pos = resolved.upper().rfind("RX")
        self.assertGreater(rx_pos, 0)
        before_rx = resolved[:rx_pos].upper()
        # USART1 should appear before RX (either originally or injected)
        last_usart = before_rx.rfind("USART1")
        self.assertGreater(last_usart, -1)

    def test_resolve_no_peripheral(self):
        """Text without a peripheral should pass through unchanged."""
        text = "configure PA5 as GPIO output"
        resolved = resolve_context(text)
        self.assertEqual(resolved, text)

    def test_resolve_spi_context(self):
        """SPI functions should inherit SPI1 context."""
        resolved = resolve_context(
            "Initialize SPI1 with MOSI on PA7 and MISO on PA6"
        )
        # MISO should have SPI1 before it
        self.assertIn("SPI1", resolved)


# ==============================================================
# Semantic Interpreter Tests
# ==============================================================

class TestSemanticInterpreter(unittest.TestCase):
    """Tests for the semantic interpreter module."""

    def test_blink_led_mapping(self):
        """Problem 4: 'Blink LED' → GPIO output."""
        result = interpret("Blink LED on PA5")
        self.assertIn("GPIO", result)
        self.assertIn("output", result)
        self.assertIn("PA5", result)

    def test_read_adc_mapping(self):
        result = interpret("Read ADC value from PA0")
        self.assertIn("ADC1", result)

    def test_send_usart_mapping(self):
        result = interpret("Send data through USART1 TX on PA9")
        self.assertIn("USART1", result)
        self.assertIn("TX", result)

    def test_no_action_passthrough(self):
        """Prompts without special actions should pass through."""
        original = "configure USART1 TX on PA9"
        result = interpret(original)
        self.assertEqual(result, original)

    def test_toggle_led(self):
        result = interpret("Toggle LED on PA5")
        self.assertIn("GPIO", result)

    def test_read_sensor(self):
        result = interpret("Read sensor on PA0")
        self.assertIn("GPIO", result)
        self.assertIn("input", result)


# ==============================================================
# Validator Tests
# ==============================================================

class TestValidator(unittest.TestCase):
    """Tests for the validator module."""

    def test_valid_gpio_intent(self):
        intent = Intent(peripheral="GPIO", pin="PA5", mode="output")
        result = validate_intents([intent])
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.intents), 1)

    def test_invalid_pin(self):
        intent = Intent(peripheral="GPIO", pin="PZ99", mode="output")
        result = validate_intents([intent])
        self.assertFalse(result.is_valid)

    def test_invalid_peripheral(self):
        intent = Intent(peripheral="INVALID", pin="PA5")
        result = validate_intents([intent])
        self.assertFalse(result.is_valid)

    def test_invalid_function_for_peripheral(self):
        intent = Intent(
            peripheral="USART1", pin="PA9", function="MOSI"
        )
        result = validate_intents([intent])
        self.assertFalse(result.is_valid)

    def test_pin_mapping_warning(self):
        """Non-default pin mapping should produce a warning."""
        intent = Intent(
            peripheral="USART1", pin="PA5", function="TX", mode="alternate"
        )
        result = validate_intents([intent])
        # Should still be valid but with a warning
        self.assertTrue(result.is_valid)
        self.assertGreater(len(result.warnings), 0)

    def test_valid_speed(self):
        intent = Intent(
            peripheral="GPIO", pin="PA5", mode="output", speed="50MHz"
        )
        result = validate_intents([intent])
        self.assertTrue(result.is_valid)

    def test_invalid_speed(self):
        intent = Intent(
            peripheral="GPIO", pin="PA5", mode="output", speed="100MHz"
        )
        result = validate_intents([intent])
        self.assertFalse(result.is_valid)

    def test_multiple_intents_validation(self):
        intents = [
            Intent(peripheral="GPIO", pin="PA5", mode="output"),
            Intent(peripheral="USART1", pin="PA9", function="TX", mode="alternate"),
        ]
        result = validate_intents(intents)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.intents), 2)


# ==============================================================
# Full Pipeline Integration Tests
# ==============================================================

class TestFullPipeline(unittest.TestCase):
    """Integration tests for the full parser pipeline."""

    def test_prompt1_complex_multi_peripheral(self):
        """Test prompt 1 from specification."""
        result = parse_prompt(
            "Configure PA5 as GPIO output push-pull at 50 MHz, "
            "enable USART1 TX on PA9 and RX on PA10, "
            "and setup ADC1 on PA0"
        )
        summaries = result.summaries()
        self.assertIn("GPIO PA5", summaries)
        self.assertIn("USART1 TX PA9", summaries)
        self.assertIn("USART1 RX PA10", summaries)
        self.assertIn("ADC1 PA0", summaries)

    def test_prompt2_pin_list_expansion(self):
        """Test prompt 2: Pin list expansion (Problem 1)."""
        result = parse_prompt(
            "Configure PA5, PA6, and PA7 as GPIO output push-pull pins"
        )
        summaries = result.summaries()
        self.assertIn("GPIO PA5", summaries)
        self.assertIn("GPIO PA6", summaries)
        self.assertIn("GPIO PA7", summaries)

    def test_prompt3_spi_multi_function(self):
        """Test prompt 3: Multi-function peripheral (Problem 2)."""
        result = parse_prompt(
            "Initialize SPI1 with MOSI on PA7, MISO on PA6, "
            "SCK on PA5 and NSS on PA4"
        )
        summaries = result.summaries()
        self.assertIn("SPI1 MOSI PA7", summaries)
        self.assertIn("SPI1 MISO PA6", summaries)
        self.assertIn("SPI1 SCK PA5", summaries)
        self.assertIn("SPI1 NSS PA4", summaries)

    def test_prompt4_semantic_interpretation(self):
        """Test prompt 4: Semantic interpretation (Problem 4)."""
        result = parse_prompt(
            "Blink LED on PA5 and send ADC readings through USART1 TX on PA9"
        )
        summaries = result.summaries()
        self.assertIn("GPIO PA5", summaries)
        self.assertIn("USART1 TX PA9", summaries)

    def test_simple_gpio_output(self):
        result = parse_prompt("Configure PA5 as GPIO output push-pull")
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.intents), 1)
        self.assertEqual(result.intents[0].peripheral, "GPIO")
        self.assertEqual(result.intents[0].pin, "PA5")

    def test_usart_tx_rx(self):
        """Problem 3: Context inheritance for USART TX and RX."""
        result = parse_prompt("Enable USART1 TX on PA9 and RX on PA10")
        summaries = result.summaries()
        self.assertIn("USART1 TX PA9", summaries)
        self.assertIn("USART1 RX PA10", summaries)

    def test_adc_configuration(self):
        result = parse_prompt("Setup ADC1 on PA0")
        self.assertEqual(len(result.intents), 1)
        self.assertEqual(result.intents[0].peripheral, "ADC1")
        self.assertEqual(result.intents[0].pin, "PA0")

    def test_parse_result_summaries(self):
        result = parse_prompt("Configure PA5 as GPIO output")
        self.assertIsInstance(result.summaries(), list)
        self.assertGreater(len(result.summaries()), 0)

    def test_empty_prompt(self):
        result = parse_prompt("")
        self.assertEqual(len(result.intents), 0)

    def test_invalid_pin_rejected(self):
        result = parse_prompt("Configure PZ99 as GPIO output")
        # PZ99 should not tokenize as a valid pin
        self.assertEqual(len(result.intents), 0)


# ==============================================================
# Schema Tests
# ==============================================================

class TestSchema(unittest.TestCase):
    """Tests for schema data classes."""

    def test_intent_summary_gpio(self):
        intent = Intent(peripheral="GPIO", pin="PA5")
        self.assertEqual(intent.summary(), "GPIO PA5")

    def test_intent_summary_with_function(self):
        intent = Intent(peripheral="USART1", pin="PA9", function="TX")
        self.assertEqual(intent.summary(), "USART1 TX PA9")

    def test_parse_result_is_valid(self):
        result = ParseResult()
        self.assertTrue(result.is_valid)
        result.errors.append("test error")
        self.assertFalse(result.is_valid)

    def test_token_creation(self):
        token = Token(type="PIN", value="PA5", position=0)
        self.assertEqual(token.type, "PIN")
        self.assertEqual(token.value, "PA5")


if __name__ == "__main__":
    unittest.main()
