# Local agent contributor instructions

- `qwen-agent/qwen-agent-src/web_agent.py` is the custom chat on loopback
  port 7860. `run_server.py` is a different BrowserQwen/workstation interface.
- The web chat and `qwen_mcp_server.py` share `create_agent()`. Keep model,
  tool, and environment configuration in that shared factory.
- Load local settings from the repository `.env`; never commit that file,
  runtime logs, tool workspace data, model weights, or cloud credentials.
- Ollama uses the OpenAI-compatible endpoint and native tool calls:
  `generate_cfg.use_raw_api=true`. Legacy tool parameter lists must become
  JSON Schema without mutating the original tool definitions.
- Preserve the original Ollama model when creating a context-size profile.
  `Modelfile.depo` sets 32768 tokens; the agent input budget defaults to 24576.
  Keep the model context and input budget consistent.
- Keep the server loopback-bound. Terminal-capable access must remain on a
  trusted private connection, never an unauthenticated public listener.
- `run-gradio.ps1` owns the Python process tree through a Windows Job Object.
  Preserve clean stop/restart behavior and the UTF-8 runtime settings.
- Test offline with `.venv\Scripts\python.exe -m unittest discover -s tests`.
  Real model requests and `/agent_run` require explicit authorization;
  reading `/config` does not run inference.
- Keep changes to vendored Qwen-Agent minimal and retain its license notices.
