"""Launch MCP Inspector against the craigpy-mcp server."""

import shutil
import subprocess
import sys


def main() -> None:
    runner = shutil.which("bunx") or shutil.which("npx")
    if not runner:
        print("Neither bunx nor npx found. Install Bun or Node.js.", file=sys.stderr)
        sys.exit(1)

    cmd = [runner, "@modelcontextprotocol/inspector", "uv", "run", "craigpy-mcp"]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass
