"""STM32F103VB Prompt Parser Package.

Provides the main entry point for parsing natural language hardware
configuration prompts into structured JSON for bare-metal firmware
generation.

Pipeline:
    User Prompt
    → Semantic Interpreter (natural language action mapping)
    → Prompt Splitter (split into sub-prompts)
    → Context Resolver (peripheral context inheritance)
    → Lexer (tokenization)
    → Parser (intent extraction)
    → Hardware Validator (rule checking)
    → Structured JSON Output
"""

from typing import List

from parser.schema import Intent, ParseResult
from parser.semantic_interpreter import interpret
from parser.prompt_splitter import split_prompt
from parser.context_resolver import resolve_context
from parser.parser import parse_sub_prompt
from parser.validator import validate_intents


def parse_prompt(prompt: str) -> ParseResult:
    """Parse a natural language hardware configuration prompt.

    This is the main entry point for the parser pipeline. It processes
    the input through all stages:
    1. Semantic interpretation (natural language → config verbs)
    2. Prompt splitting (complex → sub-prompts)
    3. Context resolution (peripheral inheritance)
    4. Lexing + Parsing (tokens → intents)
    5. Validation (hardware rule checking)

    Args:
        prompt: The natural language configuration prompt.

    Returns:
        ParseResult containing validated intents, warnings, and errors.
    """
    # Stage 1: Semantic interpretation
    interpreted = interpret(prompt)

    # Stage 2: Split into sub-prompts
    sub_prompts = split_prompt(interpreted)

    # Stage 3 & 4: Resolve context and parse each sub-prompt
    all_intents: List[Intent] = []
    for sub_prompt in sub_prompts:
        resolved = resolve_context(sub_prompt)
        intents = parse_sub_prompt(resolved)
        all_intents.extend(intents)

    # Stage 5: Validate all intents
    result = validate_intents(all_intents)

    return result
