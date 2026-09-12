# Gradio Local Agent

Локальный агент на Qwen-Agent и Ollama для работы с проектами через веб-чат, MCP и VS Code.

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
- Ollama с моделью `gpt-oss:20b` и профилем `gpt-oss:20b-depo` (или другая совместимая модель);
- SearXNG на `http://localhost:8080`, если нужен веб-поиск.

## Установка Python-зависимостей

Из корня репозитория выполните:

```powershell
python -m pip install -r requirements.txt
```

Виртуальное окружение не включено в репозиторий и не требуется. При необходимости его можно создать отдельно на конкретном компьютере.

## Настройка окружения

Скопируйте `.env.example` в `.env` и замените placeholders своими значениями. Файл `.env` не публикуйте.

При запущенном Ollama подготовьте модель и профиль из корня репозитория:

```powershell
ollama pull gpt-oss:20b
ollama create gpt-oss:20b-depo -f .\Modelfile.depo
```

Переменные `DASHSCOPE_API_KEY`, `SERPER_API_KEY` и `AMAP_TOKEN` нужны только соответствующим облачным инструментам. Реальные ключи не должны находиться в исходниках, настройках VS Code или коммитах.

## Веб-чат Gradio и подключение Depo

Чат с инструментами `terminal`, `searxng`, `deep_web_search` и постоянной памятью
запускается через `qwen-agent\qwen-agent-src\web_agent.py` на
`http://127.0.0.1:7860`. `run_server.py` запускает другой интерфейс
(BrowserQwen/workstation на порту `7864`), а не этот чат.

Веб-чат и MCP-сервер читают `.env` из корня репозитория; переменные процесса
имеют приоритет. Для Depo создайте профиль с контекстом 32768 токенов:

```powershell
ollama create gpt-oss:20b-depo -f .\Modelfile.depo
```

Используются те же веса установленной `gpt-oss:20b`; исходная модель не
изменяется, повторное скачивание весов не требуется. Затем укажите в `.env`:

```dotenv
OLLAMA_MODEL=gpt-oss:20b-depo
OLLAMA_MAX_INPUT_TOKENS=24576
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
SEARXNG_URL=http://127.0.0.1:8080
```

Запуск на Windows из корня репозитория:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run-gradio.ps1
```

Скрипт используется задачей планировщика `Gradio Local Agent` для автозапуска
при входе пользователя. Он пишет вывод в `logs\gradio.stdout.log`, ошибки —
в `logs\gradio.stderr.log`. При настройке задачи используйте этот скрипт
как аргумент `powershell.exe -NoProfile -WindowStyle Hidden -File` и корень
репозитория как рабочий каталог. Скрытое окно не мешает работе пользователя
и защищает фоновый процесс от случайного закрытия его консоли.

Остановка задачи также завершает её дочерние процессы Python, чтобы
перезапуск не оставлял старый сервер на порту 7860.

Локальный Docker backend обращается к `http://host.docker.internal:7860`
и использует Gradio API `/add_text` и `/agent_run`. Для удалённого backend
нужен отдельный доверенный VPN-доступ к этому порту; не открывайте агент
с инструментом `terminal` напрямую в Интернет. SearXNG должен быть
доступен по `SEARXNG_URL`; `beautifulsoup4` и `lxml` из `requirements.txt`
нужны инструменту `deep_web_search` для чтения найденных страниц.
Обновление страницы и чтение API-схемы не запускают модель; отправка
сообщения или вызов `/agent_run` запускают AI.

Ollama подключён через нативный OpenAI tool-calling
(`generate_cfg.use_raw_api=true`). Это необходимо для `gpt-oss:20b`:
текстовый XML-парсер старого режима теряет его нативные вызовы инструментов.
При передаче в API устаревшие списки параметров `terminal` и `storage`
преобразуются в JSON Schema; исходные определения инструментов не меняются.

Контекст Ollama по умолчанию может составлять всего 4096 токенов, чего
недостаточно для цепочек поиска Depo: сервер обрезает запрос, и модель
теряет инструкции или возвращает пустой ответ. OpenAI-совместимый API
Ollama не принимает размер контекста в запросе, поэтому он задан в
`Modelfile.depo`. Бюджет входных сообщений агента — 24576 токенов;
оставшаяся часть окна нужна для схем инструментов, рассуждений и ответа.
При смене модели согласуйте её `num_ctx` и `OLLAMA_MAX_INPUT_TOKENS`.
Рассуждения модели не отключаются.

Локальные тесты конфигурации, поиска и чтения HTML без вызовов AI:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

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