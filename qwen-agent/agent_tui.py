from qwen_agent.agents import Assistant
from qwen_agent.gui import typewriter_print

llm_cfg = {
    "model": "qwen3:14b",
    "model_type": "oai",
    "model_server": "http://localhost:11434/v1",
    "api_key": "ollama",
}

bot = Assistant(
    llm=llm_cfg,
    function_list=["terminal"],
    name="Qwen Local Agent",
    description="Локальный агент на Qwen3:14B",
)

messages = []

while True:
    try:
        query = input("\nТы: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if not query:
        continue

    if query.lower() in {"exit", "quit", "выход"}:
        break

    messages.append({"role": "user", "content": query})

    response = []
    response_plain_text = ""

    for response in bot.run(messages=messages):
        response_plain_text = typewriter_print(
            response,
            response_plain_text,
        )

    messages.extend(response)
