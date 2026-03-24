from parser.parser import parse, parse_multi

print("\nSTM32 Prompt Parser (LLM Enabled)")
print("Type 'exit' or 'quit' to stop.\n")

while True:
    prompt = input("Enter STM32 prompt: ").strip()

    if prompt.lower() in ["exit", "quit"]:
        print("Exiting parser.")
        break

    if not prompt:
        continue

    try:
        result = parse_multi(prompt)
        print("\nParsed JSON:\n")
        print(result.model_dump_json(indent=2))
        print()

    except Exception:
        try:
            result = parse(prompt)
            print("\nParsed JSON:\n")
            print(result.model_dump_json(indent=2))
            print()

        except Exception as e:
            print("\nError:", e)
            print()