#!/usr/bin/env python3
"""
Context Server for Claude Voice
Handles Vapi tool calls to provide live project context.
"""

import json
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse


def get_data_dir() -> Path:
    """Get the data directory."""
    skill_dir = Path.home() / ".claude" / "skills" / "call" / "data"
    if skill_dir.exists():
        return skill_dir
    return Path.home() / ".claude-voice"


DATA_DIR = get_data_dir()
PROJECTS_DIR = DATA_DIR / "projects"


def load_project(name: str) -> dict:
    """Load a registered project by name."""
    project_file = PROJECTS_DIR / f"{name}.json"
    if project_file.exists():
        return json.loads(project_file.read_text())

    # Try case-insensitive match
    for f in PROJECTS_DIR.glob("*.json"):
        if f.stem.lower() == name.lower():
            return json.loads(f.read_text())

    return None


def list_all_projects() -> list:
    """List all registered projects."""
    projects = []
    for f in PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            projects.append({
                "name": data.get("name", f.stem),
                "description": data.get("context", {}).get("description", ""),
                "path": data.get("path", "")
            })
        except:
            pass
    return projects


def get_project_context(project_name: str) -> dict:
    """Get context for a project."""
    project = load_project(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found. Use list_projects to see available projects."}

    ctx = project.get("context", {})
    return {
        "name": project.get("name"),
        "path": project.get("path"),
        "description": ctx.get("description", "No description"),
        "project_type": ctx.get("project_type", "Unknown"),
        "git_status": ctx.get("git_summary", "No git info"),
        "todos": ctx.get("todos", []),
        "recent_files": ctx.get("recent_files", [])[:10]
    }


def read_file(project_name: str, file_path: str) -> dict:
    """Read a file from a project."""
    project = load_project(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    project_path = Path(project.get("path", ""))
    full_path = project_path / file_path

    # Security: ensure file is within project
    try:
        full_path = full_path.resolve()
        project_path = project_path.resolve()
        if not str(full_path).startswith(str(project_path)):
            return {"error": "Access denied: file outside project directory"}
    except:
        return {"error": "Invalid path"}

    if not full_path.exists():
        return {"error": f"File not found: {file_path}"}

    if not full_path.is_file():
        return {"error": f"Not a file: {file_path}"}

    try:
        content = full_path.read_text()
        if len(content) > 2000:
            content = content[:2000] + "\n... [truncated for voice]"
        return {
            "file": file_path,
            "content": content,
            "lines": len(content.splitlines())
        }
    except Exception as e:
        return {"error": f"Could not read file: {str(e)}"}


def search_code(project_name: str, query: str) -> dict:
    """Search code in a project using grep."""
    project = load_project(project_name)
    if not project:
        return {"error": f"Project '{project_name}' not found"}

    project_path = project.get("path", "")
    if not Path(project_path).exists():
        return {"error": f"Project path not found: {project_path}"}

    try:
        result = subprocess.run(
            ["grep", "-r", "-n", "-i", "--include=*.py", "--include=*.js",
             "--include=*.ts", "--include=*.tsx", "--include=*.swift",
             "--include=*.json", "--include=*.md", query, project_path],
            capture_output=True, text=True, timeout=10
        )

        matches = result.stdout.strip().split("\n")[:10]
        if not matches or matches == ['']:
            return {"query": query, "matches": [], "message": "No matches found"}

        cleaned = []
        for m in matches:
            if project_path in m:
                m = m.replace(project_path + "/", "")
            cleaned.append(m[:200])

        return {"query": query, "matches": cleaned}
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


class VapiHandler(BaseHTTPRequestHandler):
    """Handle Vapi webhook requests."""

    def log_message(self, format, *args):
        print(f"[VAPI] {args[0]}")

    def send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()

        try:
            data = json.loads(body) if body else {}
        except:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        print(f"[VAPI] Request: {json.dumps(data, indent=2)[:500]}")

        message = data.get("message", {})

        if message.get("type") == "tool-calls":
            tool_calls = message.get("toolCalls", [])
            results = []

            for call in tool_calls:
                tool_call_id = call.get("id")
                function = call.get("function", {})
                name = function.get("name")
                args = function.get("arguments", {})

                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except:
                        args = {}

                print(f"[VAPI] Tool call: {name}({args})")

                if name == "list_projects":
                    result = list_all_projects()
                elif name == "get_project_context":
                    result = get_project_context(args.get("project_name", ""))
                elif name == "read_file":
                    result = read_file(args.get("project_name", ""), args.get("file_path", ""))
                elif name == "search_code":
                    result = search_code(args.get("project_name", ""), args.get("query", ""))
                else:
                    result = {"error": f"Unknown tool: {name}"}

                results.append({
                    "toolCallId": tool_call_id,
                    "result": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                })

            self.send_json({"results": results})
            return

        self.send_json({"status": "ok"})

    def do_GET(self):
        self.send_json({
            "status": "running",
            "service": "Claude Voice Context Server",
            "projects": len(list(PROJECTS_DIR.glob("*.json"))) if PROJECTS_DIR.exists() else 0
        })


def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description="Context server for Claude Voice")
        parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
        args = parser.parse_args()

    port = getattr(args, 'port', 8765)
    server = HTTPServer(("0.0.0.0", port), VapiHandler)

    print(f"🎙️  Context server running on http://localhost:{port}")
    print(f"📁 Projects: {len(list(PROJECTS_DIR.glob('*.json'))) if PROJECTS_DIR.exists() else 0} registered")
    print(f"\nExpose with: npx localtunnel --port {port}")
    print("Then run: claude-voice setup  (to update server URL)\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")


if __name__ == "__main__":
    main()
