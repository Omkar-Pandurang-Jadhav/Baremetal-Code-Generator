import re

INTENT_PATTERN = re.compile(
    r"""
    (?=
        \bconfigure\b |
        \benable\b |
        \bsetup\b |
        \binitialize\b |
        \band\s+(?:rx|tx|mosi|miso|scl|sda)\b
    )
    """,
    re.IGNORECASE | re.VERBOSE
)

def split_prompt(prompt: str):

    parts = INTENT_PATTERN.split(prompt)

    return [p.strip(" ,.") for p in parts if p.strip()]