from parser.parser import parse, parse_multi

while True:
    prompt = input("Enter STM32 prompt: ")

    if prompt.lower() in ["exit", "quit"]:
        print("Exiting parser.")
        break

    try:
        # Try multi-intent parsing first
        result = parse_multi(prompt)
        print("\nParsed JSON:\n")
        print(result.model_dump_json(indent=2))
        print()

    except Exception:
        try:
            # Fallback to single intent parsing
            result = parse(prompt)
            print("\nParsed JSON:\n")
            print(result.model_dump_json(indent=2))
            print()

        except Exception as e:
            print("\nError:", e)
            print()