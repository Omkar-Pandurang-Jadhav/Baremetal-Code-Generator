"""
Normalization layer for STM32 prompt parser.

Uses Gemini to convert messy, unstructured user input
into clean, structured prompts suitable for parsing.
"""
import os
print("📂 NORMALIZER FILE:", os.path.abspath(__file__))
from parser.llm_client import get_gemini_client


    
    
client = get_gemini_client()  
def normalize_prompt(prompt: str) -> str:
    print("🚀 NORMALIZER CALLED")

    

    system_prompt ="""
You are an STM32 embedded systems assistant.

Your task is to normalize user input into a clean and structured
STM32 configuration instruction.

STRICT RULES:
- Do NOT change technical meaning
- Do NOT invent new peripherals or pins
- Do NOT assume missing hardware
- Expand shorthand (pa5 → PA5, tx → TX)
- Add missing connectors like "on", "and"
- Keep all commands intact (multi-command supported)
- Output ONLY the normalized sentence (no explanation)

EXAMPLES:

Input: pa5 output 50mhz
Output: Configure PA5 as GPIO output push-pull at 50 MHz

Input: usart1 tx pa9 rx pa10
Output: Enable USART1 TX on PA9 and RX on PA10

Input: adc1 pa0 read sensor
Output: Setup ADC1 on PA0

Input: pa5 led and uart1 tx pa9
Output: Configure PA5 as GPIO output and enable USART1 TX on PA9
"""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash",contents=f"{system_prompt}  \n\nInput:  {prompt} \nOutput:")

        normalized = response.text.strip()

        print("🔵 INPUT:", prompt)
        print("🟢 OUTPUT:", normalized)

        return normalized

    except Exception as e:
        print("❌ Gemini failed:", e)
        return prompt