from html.parser import HTMLParser
from typing import Dict, List, Union

import requests
from qwen_agent.agents.memo_assistant import MemoAssistant
from qwen_agent.gui import WebUI
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.tools.simple_doc_parser import SimpleDocParser
import terminal_tool


SEARXNG_URL = "http://localhost:8080"


class _SearXNGResultParser(HTMLParser):
    def __init__(self, max_results: int):
        super().__init__()
        self.max_results = max_results
        self.results: List[Dict[str, str]] = []
        self._current: Dict[str, str] = {}
        self._text: List[str] = []
        self._field = None
        self._in_article = False

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        attributes = dict(attrs)
        if (tag == "article" and len(self.results) < self.max_results and
            "result" in attributes.get("class", "").split()):
            self._in_article = True
            self._current = {}
        elif self._in_article and tag == "h3":
            self._field = "title"
            self._text = []
        elif self._in_article and tag == "p" and "content" in attributes.get("class", "").split():
            self._field = "snippet"
            self._text = []
        elif self._in_article and tag == "a" and "href" in attributes and "url_header" not in attributes.get("class", ""):
            self._current.setdefault("url", attributes["href"])

    def handle_endtag(self, tag: str) -> None:
        if self._field and ((tag == "h3" and self._field == "title") or
                            (tag == "p" and self._field == "snippet")):
            self._current[self._field] = " ".join("".join(self._text).split())
            self._field = None
            self._text = []
        elif tag == "article" and self._in_article:
            if self._current.get("title") and self._current.get("url"):
                self.results.append(self._current)
            self._in_article = False

    def handle_data(self, data: str) -> None:
        if self._field:
            self._text.append(data)


@register_tool("searxng")
class SearXNGSearch(BaseTool):
    name = "searxng"
    description = "Search the web through the local SearXNG instance and return titles, URLs, and snippets."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    }

    @staticmethod
    def search(query: str, max_results: int = 10) -> List[Dict[str, str]]:
        response = requests.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json", "number_of_results": max_results},
            timeout=20,
        )
        if response.ok:
            return response.json().get("results", [])[:max_results]
        if response.status_code != 403:
            response.raise_for_status()

        response = requests.get(f"{SEARXNG_URL}/search", params={"q": query}, timeout=20)
        response.raise_for_status()
        parser = _SearXNGResultParser(max_results)
        parser.feed(response.text)
        return parser.results

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        query = params["query"].strip()
        if not query:
            raise ValueError("Search query cannot be empty")
        max_results = max(1, min(int(params.get("max_results", 10)), 20))

        results = self.search(query, max_results)

        if not results:
            return f'No search results found for "{query}".'
        return "\n\n".join(
            f"[{index}] {result.get('title', '')}\n{result.get('url', '')}\n{result.get('snippet', result.get('content', ''))}"
            for index, result in enumerate(results, 1)
        )


@register_tool("deep_web_search")
class DeepWebSearch(BaseTool):
    name = "deep_web_search"
    description = (
        "Search with local SearXNG and read the full text of the most relevant pages. "
        "Use this when snippets are not enough to answer the question."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "max_pages": {"type": "integer", "minimum": 1, "maximum": 5},
            "max_chars_per_page": {"type": "integer", "minimum": 1000, "maximum": 12000},
        },
        "required": ["query"],
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        query = params["query"].strip()
        max_pages = max(1, min(int(params.get("max_pages", 3)), 5))
        max_chars = max(1000, min(int(params.get("max_chars_per_page", 6000)), 12000))
        search_results = SearXNGSearch.search(query)[:max_pages]
        pages = []

        for index, result in enumerate(search_results, 1):
            url = result.get("url", result.get("link", ""))
            if not url:
                continue
            try:
                parsed = SimpleDocParser().call({"url": url})
                if isinstance(parsed, str):
                    text = parsed.strip()
                else:
                    text = "\n".join(
                        item.get("text", item.get("table", "")) if isinstance(item, dict) else str(item)
                        for page in parsed
                        for item in page.get("content", []) if isinstance(page, dict)
                    ).strip()
                if text:
                    pages.append(f"[{index}] {result.get('title', '')}\n{url}\n{text[:max_chars]}")
            except Exception as error:
                pages.append(f"[{index}] {result.get('title', '')}\n{url}\nНе удалось прочитать страницу: {error}")

        if not pages:
            return f'Не удалось получить полный текст страниц по запросу "{query}".'
        return "\n\n".join(pages)

llm_cfg = {
    "model": "qwen3:14b",
    "model_type": "oai",
    "model_server": "http://localhost:11434/v1",
    "api_key": "ollama",
}

system_message = (
    "Отвечай пользователю всегда на русском языке. "
    "Переводи на русский найденные в интернете материалы, названия и цитаты, "
    "сохраняя URL без изменений. Оригинальный текст или ответ на другом языке "
    "выдавай только если пользователь явно попросил об этом. "
    "У тебя есть постоянная память. Если пользователь просит что-то запомнить, "
    "сохрани это через storage. Используй сохранённые предпочтения и факты в "
    "следующих диалогах, но не сохраняй пароли, токены и другие секреты."
)

def create_agent():
    return MemoAssistant(
        llm=llm_cfg,
        function_list=["terminal", "searxng", "deep_web_search"],
        system_message=system_message,
        name="Локальный Qwen Agent",
        description="Локальный агент на Qwen3:14B",
    )


if __name__ == "__main__":
    WebUI(create_agent()).run(
        server_name="127.0.0.1",
        server_port=7860,
    )
