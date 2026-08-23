# Gradio Local Agent

Локальный агент Qwen3:14B для работы с проектами через MCP и VS Code.

## Возможности

- чат-агент с локальной моделью Ollama;
- выполнение команд через инструмент `terminal`;
- поиск через локальный SearXNG;
- постоянная память агента;
- чат-участник `@qwen` для VS Code.

## Требования

- Windows, macOS или Linux;
- Python 3.12 или новее;
- Node.js 18 или новее для сборки расширения;
- Ollama с моделью `qwen3:14b`;
- SearXNG на `http://localhost:8080`, если нужен веб-поиск.

## Установка Python-зависимостей

Из корня репозитория выполните:

```powershell
python -m pip install -r requirements.txt
```

Виртуальное окружение не включено в репозиторий и не требуется. При необходимости его можно создать отдельно на конкретном компьютере.

## Настройка окружения

Скопируйте `.env.example` в `.env` и замените placeholders своими значениями. Файл `.env` не публикуйте.

Для локального Ollama обычно достаточно запустить:

```powershell
ollama serve
ollama pull qwen3:14b
```

Переменные `DASHSCOPE_API_KEY`, `SERPER_API_KEY` и `AMAP_TOKEN` нужны только соответствующим облачным инструментам. Реальные ключи не должны находиться в исходниках, настройках VS Code или коммитах.

## Запуск агента в терминале

```powershell
cd qwen-agent
python agent.py
```

Для выхода введите `exit`, `quit` или `выход`.

## Запуск MCP-сервера

Из каталога сервера:

```powershell
cd qwen-agent/qwen-agent-src
python qwen_mcp_server.py
```

Сервер использует stdio и предназначен для запуска MCP-клиентом, например расширением VS Code.

## Установка и настройка расширения VS Code

Перейдите в каталог расширения и установите зависимости сборки:

```powershell
cd qwen-vscode-extension
npm install
npm run check
npm run bundle
```

Для создания устанавливаемого пакета выполните:

```powershell
npx vsce package --no-dependencies
```

Затем в VS Code выполните `Developer: Install Extension from Location...` и выберите созданный `.vsix`.

После установки задайте настройки:

- `qwenLocalAgent.rootPath` — абсолютный путь к каталогу `qwen-agent` из этого репозитория;
- `qwenLocalAgent.pythonPath` — `python` или абсолютный путь к системному Python.

Расширение не зависит от открытой папки проекта. После изменения настроек выполните `Developer: Reload Window`.

## MCP-конфигурация VS Code

Файл `.vscode/mcp.json` содержит переносимый пример для запуска MCP-сервера из открытой копии репозитория. Для постоянной установки расширения используйте настройки `qwenLocalAgent.rootPath` и `qwenLocalAgent.pythonPath`.

## Публикация

Перед публикацией проверьте, что в репозитории нет `.env`, ключей, локальных виртуальных окружений, `node_modules`, `.vsix` и кэшей. Затем:

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```