from qwen_agent.tools.base import BaseTool, register_tool
import json5
import subprocess


@register_tool("terminal", allow_overwrite=True)
class TerminalTool(BaseTool):
    description = (
        "Execute a PowerShell command on the local Windows computer. "
        "Accepts exactly one argument: command."
    )

    parameters = [
        {
            "name": "command",
            "type": "string",
            "description": "PowerShell command to execute.",
            "required": True,
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        args = json5.loads(params)
        command = args.get("command", "").strip()

        if not command:
            return "Error: command is empty."

        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )

            output = []

            if result.stdout:
                output.append(result.stdout.rstrip())

            if result.stderr:
                output.append("[stderr]")
                output.append(result.stderr.rstrip())

            output.append(f"[exit_code={result.returncode}]")

            return "\n".join(output)

        except subprocess.TimeoutExpired:
            return "Error: command timed out after 60 seconds."
        except Exception as exc:
            return f"Error executing command: {exc}"
