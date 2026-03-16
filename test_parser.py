import json
from parser import parse_prompt


def intent_to_dict(intent):
    """Convert Intent dataclass to dictionary."""
    return {
        "peripheral": intent.peripheral,
        "function": intent.function,
        "pin": intent.pin,
        "mode": intent.mode,
        "output_type": intent.output_type,
        "speed": intent.speed,
        "pull": intent.pull,
    }


def main():
    print("\nSTM32 Prompt Parser")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        prompt = input("Enter STM32 prompt: ").strip()

        if prompt.lower() in ["exit", "quit"]:
            print("\nExiting parser.\n")
            break

        if not prompt:
            continue

        try:
            result = parse_prompt(prompt)

            output = {
                "intents": [intent_to_dict(i) for i in result.intents],
                "warnings": result.warnings,
                "errors": result.errors,
            }

            print("\nParsed JSON:\n")
            print(json.dumps(output, indent=2))
            print()

        except Exception as e:
            print("\nError:", str(e))
            print()


if __name__ == "__main__":
    main()