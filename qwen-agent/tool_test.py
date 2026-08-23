from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool


@register_tool("get_current_directory")
class GetCurrentDirectory(BaseTool):
    description = "Returns the current working directory."
    parameters = []

    def call(self, params, **kwargs):
        import os
        return os.getcwd()


bot = Assistant(
    llm={
        "model": "qwen3:14b",
        "model_server": "http://localhost:11434/v1",
        "api_key": "ollama",
    },
    function_list=["get_current_directory"],
)

messages = [
    {
        "role": "user",
        "content": (
            "Используй инструмент get_current_directory и сообщи текущую "
            "рабочую директорию. Ответь по-русски."
        ),
    }
]

for response in bot.run(messages):
    print(response)
