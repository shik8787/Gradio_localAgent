from qwen_agent.agents import Assistant
import terminal_tool


bot = Assistant(
    llm={
        "model": "qwen3:14b",
        "model_server": "http://localhost:11434/v1",
        "api_key": "ollama",
    },
    function_list=["terminal"],
)

print("Qwen-Agent запущен. Для выхода: exit")
print()

while True:
    try:
        user_input = input("Ты: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if not user_input:
        continue

    if user_input.lower() in {"exit", "quit", "выход"}:
        break

    messages = [
        {
            "role": "user",
            "content": user_input,
        }
    ]

    print("Агент: ", end="", flush=True)

    try:
        for response in bot.run(messages):
            # Qwen-Agent возвращает сообщения/дельты по мере генерации.
            if not response:
                continue

            last = response[-1] if isinstance(response, list) else response

            if isinstance(last, dict):
                content = last.get("content", "")
                if content:
                    print(content, end="", flush=True)

        print()

    except Exception as exc:
        print(f"\n[Ошибка агента: {exc}]")

