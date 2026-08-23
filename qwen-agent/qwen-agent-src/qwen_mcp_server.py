import asyncio
from typing import Any

from mcp import types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from web_agent import create_agent


agent = None
conversation = []


def tool_definition() -> types.Tool:
    return types.Tool(
        name="ask_qwen",
        description=(
            "Send a request to the local Qwen3:14B project agent. "
            "The agent can inspect and modify the current project with terminal, "
            "search the web through local SearXNG, and use persistent memory."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The user's request for the local project agent.",
                }
            },
            "required": ["prompt"],
        },
    )


async def list_tools() -> list[types.Tool]:
    return [tool_definition()]


async def call_tool(tool_name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if tool_name != "ask_qwen":
        return [types.TextContent(type="text", text=f"Unknown tool: {tool_name}")]

    prompt = str(arguments.get("prompt", "")).strip()
    if not prompt:
        return [types.TextContent(type="text", text="Поле prompt не должно быть пустым.")]

    conversation.append({"role": "user", "content": prompt})
    try:
        global agent
        if agent is None:
            agent = create_agent()
        responses = agent.run_nonstream(conversation)
        conversation.extend(responses)
        answer = "Агент не вернул текстовый ответ."
        for message in reversed(responses):
            content = message.get("content") if isinstance(message, dict) else message.content
            if content:
                answer = content
                break
        return [types.TextContent(type="text", text=answer)]
    except Exception as error:
        conversation.pop()
        return [types.TextContent(type="text", text=f"Ошибка локального агента: {error}")]


server = Server(
    "qwen-local-agent",
    version="1.0.0",
    instructions="Локальный Qwen3:14B агент для работы с проектами.",
)
server.list_tools()(list_tools)
server.call_tool()(call_tool)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="qwen-local-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
                instructions="Локальный Qwen3:14B агент для работы с проектами.",
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
