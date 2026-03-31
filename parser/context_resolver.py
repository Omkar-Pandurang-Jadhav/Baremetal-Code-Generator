import re

USART_RE = re.compile(r'\bUSART([1-3])\b', re.IGNORECASE)

def propagate_context(segments):
    """
    Propagate peripheral context between prompt segments.
    Example:
    'USART1 TX on PA9', 'RX on PA10'
    -> second becomes 'USART1 RX on PA10'
    """

    current_usart = None
    resolved = []

    for seg in segments:

        usart_match = USART_RE.search(seg)

        if usart_match:
            current_usart = usart_match.group(0)

        elif current_usart and re.search(r'\b(rx|tx)\b', seg, re.IGNORECASE):
            seg = f"{current_usart} {seg}"

        resolved.append(seg)

    return resolved