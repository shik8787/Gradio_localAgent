from qwen_agent.agents import Assistant

# Importing the module registers the tool.
import terminal_tool


bot = Assistant(
    llm={
        "model": "qwen3:14b",
        "model_server": "http://localhost:11434/v1",
        "api_key": "ollama",
    },
    function_list=["terminal"],
)

messages = [
    {
        "role": "user",
        "content": (
            "Используй terminal и выполни команду "
            "`echo TEST123`. После выполнения ответь только TEST123."
        ),
    }
]

for response in bot.run(messages):
    print(response)
