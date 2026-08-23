# Qwen Local Agent for VS Code

This local extension adds the `@qwen` chat participant and starts the Qwen Agent MCP server from a configured installation path.

## Install for development

1. Open any folder in VS Code.
2. Open the `qwen-vscode-extension` folder in a second VS Code window, or use `Developer: Install Extension from Location...` after packaging it.
3. Run `npm install` in this folder.
4. Press `F5` to launch an Extension Development Host.
5. In Chat, type `@qwen`.

Set `qwenLocalAgent.rootPath` to the `qwen-agent` directory containing `qwen-agent-src` and set `qwenLocalAgent.pythonPath` to `python` or an absolute path to a system Python. The extension does not depend on the opened workspace.
