const path = require('path');
const vscode = require('vscode');
const { spawn } = require('child_process');

const MCP_REQUEST_TIMEOUT_MS = 15 * 60 * 1000;

class QwenMcpBridge {
    constructor(paths) {
        this.paths = paths;
        this.process = null;
        this.nextRequestId = 1;
        this.pending = new Map();
        this.buffer = '';
    }

    async start() {
        this.process = spawn(this.paths.python, [this.paths.server], {
            cwd: this.paths.cwd,
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: true,
        });
        this.process.stdout.setEncoding('utf8');
        this.process.stdout.on('data', (chunk) => this.read(chunk));
        this.process.on('error', (error) => this.failPending(error));
        this.process.on('exit', (code) => {
            if (code !== 0) {
                this.failPending(new Error(`MCP server exited with code ${code}`));
            }
        });
        await this.request('initialize', {
            protocolVersion: '2025-03-26',
            capabilities: {},
            clientInfo: { name: 'qwen-vscode-extension', version: '0.1.1' },
        });
        this.notify('notifications/initialized');
        return this;
    }

    read(chunk) {
        this.buffer += chunk;
        const lines = this.buffer.split('\n');
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
                    pending.reject(new Error(message.error.message || 'MCP request failed'));
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
                reject(new Error(`MCP request timed out after ${MCP_REQUEST_TIMEOUT_MS / 1000} seconds`));
            }, MCP_REQUEST_TIMEOUT_MS);
            this.pending.set(id, { resolve, reject, timer });
            this.process.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method, params })}\n`);
        });
    }

    notify(method, params = {}) {
        this.process.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', method, params })}\n`);
    }

    async ask(prompt) {
        const result = await this.request('tools/call', {
            name: 'ask_qwen',
            arguments: { prompt },
        });
        return (result?.content || [])
            .filter((item) => item.type === 'text')
            .map((item) => item.text)
            .join('\n');
    }

    failPending(error) {
        for (const pending of this.pending.values()) {
            clearTimeout(pending.timer);
            pending.reject(error);
        }
        this.pending.clear();
    }

    close() {
        this.failPending(new Error('MCP server stopped'));
        this.process?.kill();
        this.process = null;
    }
}

let bridge;

function projectPaths() {
    const configuredRoot = vscode.workspace
        .getConfiguration('qwenLocalAgent')
        .get('rootPath', '');
    if (!configuredRoot) {
        throw new Error('Укажите путь к каталогу qwen-agent в настройке qwenLocalAgent.rootPath.');
    }

    const projectRoot = path.resolve(configuredRoot);
    const python = vscode.workspace
        .getConfiguration('qwenLocalAgent')
        .get('pythonPath', 'python');
    return {
        cwd: path.join(projectRoot, 'qwen-agent-src'),
        python,
        server: path.join(projectRoot, 'qwen-agent-src', 'qwen_mcp_server.py'),
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
        const text = await qwen.ask(`Работай с проектом ${projectRoot}.\n\n${request.prompt}`);
        response.markdown(text);
    } catch (error) {
        bridge?.close();
        bridge = undefined;
        response.markdown(`Не удалось подключиться к локальному Qwen: ${error.message}`);
    }
}

function activate(context) {
    const participant = vscode.chat.createChatParticipant('local.qwen', handleRequest);
    participant.iconPath = vscode.Uri.file(path.join(context.extensionPath, 'qwen.svg'));
    context.subscriptions.push(participant);
}

function deactivate() {
    bridge?.close();
}

module.exports = { activate, deactivate };
