import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qwen-agent" / "qwen-agent-src"))

from web_agent import SearXNGSearch, SimpleDocParser, create_agent, llm_cfg


class WebAgentTests(unittest.TestCase):
    def test_agent_registers_local_tools_without_inference(self):
        with patch("requests.sessions.Session.request", side_effect=AssertionError("Network call")):
            agent = create_agent()
        self.assertEqual(set(agent.function_map), {"terminal", "searxng", "deep_web_search", "storage"})
        self.assertIn(llm_cfg["model"], agent.description)
        self.assertTrue(agent.llm.use_raw_api)
        self.assertGreater(agent.llm.generate_cfg["max_input_tokens"], 4096)

    def test_native_api_preserves_calls_and_converts_legacy_parameter_lists(self):
        agent = create_agent()
        call = SimpleNamespace(
            id="call-search",
            function=SimpleNamespace(name="searxng", arguments='{"query":"Python docs"}'),
        )
        chunk = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(
            content=None, reasoning_content=None, tool_calls=[call],
        ))])
        functions = [tool.function for tool in agent.function_map.values()]
        with patch.object(agent.llm, "_chat_complete_create", return_value=iter([chunk])) as complete:
            responses = list(agent.llm.chat(
                [{"role": "user", "content": "Find Python docs"}], functions=functions,
            ))[-1]
        self.assertEqual(responses[0].function_call.name, "searxng")
        schemas = {tool["function"]["name"]: tool["function"]["parameters"]
                   for tool in complete.call_args.kwargs["tools"]}
        self.assertTrue(all(schema["type"] == "object" for schema in schemas.values()))
        self.assertEqual(schemas["terminal"]["required"], ["command"])
        self.assertEqual(schemas["terminal"]["properties"]["command"]["type"], "string")
        self.assertEqual(schemas["searxng"], SearXNGSearch.parameters)
        self.assertIsInstance(agent.function_map["terminal"].parameters, list)

    def test_search_limits_json_results(self):
        response = Mock(ok=True)
        response.json.return_value = {"results": [{"title": "one"}, {"title": "two"}]}
        with patch("web_agent.requests.get", return_value=response) as get:
            self.assertEqual(SearXNGSearch.search("documentation", 1), [{"title": "one"}])
        self.assertEqual(get.call_args.kwargs["params"]["format"], "json")

    def test_search_falls_back_to_html_when_json_is_disabled(self):
        forbidden = Mock(ok=False, status_code=403)
        html = Mock(text='<article class="result"><h3><a href="https://example.org">Title</a>'
                         '</h3><p class="content">Snippet</p></article>')
        with patch("web_agent.requests.get", side_effect=[forbidden, html]):
            self.assertEqual(SearXNGSearch.search("documentation"),
                             [{"title": "Title", "url": "https://example.org", "snippet": "Snippet"}])

    def test_html_reader_dependencies_and_text_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "page.html"
            source.write_text("<html><title>Test</title><body><p>Readable page</p></body></html>",
                              encoding="utf-8")
            parser = SimpleDocParser({"path": str(Path(directory) / "cache")})
            self.assertIn("Readable page", parser.call({"url": str(source)}))


if __name__ == "__main__":
    unittest.main()
