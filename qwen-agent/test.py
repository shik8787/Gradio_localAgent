from qwen_agent.agents import Assistant

llm_cfg = {
    "model": "qwen3:14b",
    "model_server": "http://localhost:11434/v1",
    "api_key": "ollama",
}

bot = Assistant(
    llm=llm_cfg,
    function_list=[],
)

messages = [
    {
        "role": "user",
        "content": "Ответь по-русски одним предложением: привет!",
    }
]

for response in bot.run(messages):
    print(response)
