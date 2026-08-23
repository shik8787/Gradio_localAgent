// extension.js
var path = require("path");
var vscode = require("vscode");
var { spawn } = require("child_process");
var MCP_REQUEST_TIMEOUT_MS = 15 * 60 * 1e3;
var QwenMcpBridge = class {
  constructor(paths) {
    this.paths = paths;
    this.process = null;
    this.nextRequestId = 1;
    this.pending = /* @__PURE__ */ new Map();
    this.buffer = "";
  }
  async start() {
    this.process = spawn(this.paths.python, [this.paths.server], {
      cwd: this.paths.cwd,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true
    });
    this.process.stdout.setEncoding("utf8");
    this.process.stdout.on("data", (chunk) => this.read(chunk));
    this.process.on("error", (error) => this.failPending(error));
    this.process.on("exit", (code) => {
      if (code !== 0) {
        this.failPending(new Error(`MCP server exited with code ${code}`));
      }
    });
    await this.request("initialize", {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: { name: "qwen-vscode-extension", version: "0.1.1" }
    });
    this.notify("notifications/initialized");
    return this;
  }
  read(chunk) {
    this.buffer += chunk;
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop();
    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }
      try {
        const message = JSON.parse(line);
        const pending = this.pending.get(message.id);
        if (!pending) {
          continue;
        }
        this.pending.delete(message.id);
        clearTimeout(pending.timer);
        if (message.error) {
          pending.reject(new Error(message.error.message || "MCP request failed"));
        } else {
          pending.resolve(message.result);
        }
      } catch (error) {
        this.failPending(error);
      }
    }
  }
  request(method, params = {}) {
    const id = this.nextRequestId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`MCP request timed out after ${MCP_REQUEST_TIMEOUT_MS / 1e3} seconds`));
      }, MCP_REQUEST_TIMEOUT_MS);
      this.pending.set(id, { resolve, reject, timer });
      this.process.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}
`);
    });
  }
  notify(method, params = {}) {
    this.process.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", method, params })}
`);
  }
  async ask(prompt) {
    const result = await this.request("tools/call", {
      name: "ask_qwen",
      arguments: { prompt }
    });
    return (result?.content || []).filter((item) => item.type === "text").map((item) => item.text).join("\n");
  }
  failPending(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }
  close() {
    this.failPending(new Error("MCP server stopped"));
    this.process?.kill();
    this.process = null;
  }
};
var bridge;
function projectPaths() {
  const configuredRoot = vscode.workspace.getConfiguration("qwenLocalAgent").get("rootPath", "");
  if (!configuredRoot) {
    throw new Error("\u0423\u043A\u0430\u0436\u0438\u0442\u0435 \u043F\u0443\u0442\u044C \u043A \u043A\u0430\u0442\u0430\u043B\u043E\u0433\u0443 qwen-agent \u0432 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0435 qwenLocalAgent.rootPath.");
  }
  const projectRoot = path.resolve(configuredRoot);
  const python = vscode.workspace.getConfiguration("qwenLocalAgent").get("pythonPath", "python");
  return {
    cwd: path.join(projectRoot, "qwen-agent-src"),
    python,
    server: path.join(projectRoot, "qwen-agent-src", "qwen_mcp_server.py")
  };
}
async function getBridge() {
  if (!bridge) {
    bridge = await new QwenMcpBridge(projectPaths()).start();
  }
  return bridge;
}
async function handleRequest(request, _context, response, token) {
  if (token.isCancellationRequested) {
    return;
  }
  try {
    const qwen = await getBridge();
    const projectRoot = projectPaths().cwd;
    const text = await qwen.ask(`\u0420\u0430\u0431\u043E\u0442\u0430\u0439 \u0441 \u043F\u0440\u043E\u0435\u043A\u0442\u043E\u043C ${projectRoot}.

${request.prompt}`);
    response.markdown(text);
  } catch (error) {
    bridge?.close();
    bridge = void 0;
    response.markdown(`\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u043F\u043E\u0434\u043A\u043B\u044E\u0447\u0438\u0442\u044C\u0441\u044F \u043A \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u043E\u043C\u0443 Qwen: ${error.message}`);
  }
}
function activate(context) {
  const participant = vscode.chat.createChatParticipant("local.qwen", handleRequest);
  participant.iconPath = vscode.Uri.file(path.join(context.extensionPath, "qwen.svg"));
  context.subscriptions.push(participant);
}
function deactivate() {
  bridge?.close();
}
module.exports = { activate, deactivate };
