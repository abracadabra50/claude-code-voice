#!/usr/bin/env python3
"""
Context Server for Claude Code Voice
Handles Vapi webhooks: tool calls, inbound calls, and call completion.
"""

import json
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import argparse


def get_data_dir() -> Path:
    """Get the data directory."""
    skill_dir = Path.home() / ".claude" / "skills" / "call" / "data"
    if skill_dir.exists():
        return skill_dir
    return Path.home() / ".claude-code-voice"


DATA_DIR = get_data_dir()
PROJECTS_DIR = DATA_DIR / "projects"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
CONFIG_FILE = DATA_DIR / "config.json"


def load_config() -> dict:
    """Load configuration."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict):
    """Save configuration."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_voice_config(config: dict) -> dict:
    """Get voice configuration from config or defaults."""
    return {
        "provider": config.get("voice_provider", "openai"),
        "voiceId": config.get("voice_id", "alloy")
    }


def get_model_config(config: dict) -> str:
    """Get model name from config or default."""
    return config.get("model", "claude-opus-4-5-20251101")


def ensure_dirs():
    """Ensure directories exist."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


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


def build_system_prompt(project: dict, topic: str = "general discussion") -> str:
    """Build rich system prompt for voice assistant."""
    context = project.get("context", {})

    return f"""You are Claude, a technical co-pilot having a phone conversation with a developer.

PERSONALITY:
- Warm, friendly, conversational - like a colleague on a call
- Keep responses SHORT - 1-2 sentences usually. This is voice, not text.
- Technical but explains in plain language when needed
- Proactive - suggest ideas, spot issues, help brainstorm

PROJECT: {project.get('name', 'Unknown')}
Type: {context.get('project_type', 'Unknown')}
Description: {context.get('description', 'No description')}
Path: {project.get('path', '')}

GIT STATUS:
{context.get('git_summary', 'No git info')}
Recent commits: {chr(10).join(context.get('recent_commits', ['No recent commits'])[:5])}

CURRENT TODOS:
{chr(10).join(['- ' + t for t in context.get('todos', ['No todos'])][:10]) or 'No todos'}

RECENT FILES:
{chr(10).join(context.get('recent_files', ['No files tracked'])[:10])}

DISCUSSION TOPIC: {topic}

You have tools available to:
- list_projects: See all registered projects
- get_project_context: Get fresh context for any project
- read_file: Read a specific file (summarize for voice)
- search_code: Search for code patterns

Use tools when you need LIVE data. The context above is a snapshot.
Keep responses brief and conversational. Ask clarifying questions. Help brainstorm."""


def get_most_recent_project() -> dict:
    """Get the most recently updated project."""
    projects = []
    for f in PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            projects.append((data.get("last_context_update", ""), data))
        except:
            pass

    if projects:
        projects.sort(key=lambda x: x[0], reverse=True)
        return projects[0][1]
    return None


def handle_assistant_request(data: dict) -> dict:
    """Handle inbound call - return assistant config based on caller."""
    message = data.get("message", {})
    call = message.get("call", {})
    caller_phone = call.get("customer", {}).get("number", "")

    print(f"[INBOUND] Call from: {caller_phone}")

    config = load_config()

    # Check if caller is recognized
    users = config.get("users", {})
    user = users.get(caller_phone)

    # Fallback: check if it's the main configured user
    if not user and config.get("user_phone") == caller_phone:
        user = {"name": "there", "last_project": None}

    if not user:
        print(f"[INBOUND] Unknown caller: {caller_phone}")
        return {
            "assistant": {
                "model": {
                    "provider": "anthropic",
                    "model": get_model_config(config),
                    "temperature": 0.7
                },
                "voice": get_voice_config(config),
                "firstMessage": "Hey! I don't recognize this number. If you've set up Claude Voice, make sure you're calling from your registered phone number."
            }
        }

    # Load their project
    project_name = user.get("last_project")
    project = None

    if project_name:
        project = load_project(project_name)

    if not project:
        project = get_most_recent_project()

    if not project:
        return {
            "assistant": {
                "model": {
                    "provider": "anthropic",
                    "model": get_model_config(config),
                    "temperature": 0.7
                },
                "voice": get_voice_config(config),
                "firstMessage": f"Hey {user.get('name', 'there')}! I don't see any projects registered yet. Run 'claude-code-voice register' in a project directory first."
            }
        }

    print(f"[INBOUND] Loading project: {project.get('name')}")

    # Update user's last_project for transcript saving
    if caller_phone and project:
        users = config.get("users", {})
        if caller_phone in users:
            users[caller_phone]["last_project"] = project.get("name")
            config["users"] = users
            save_config(config)

    system_prompt = build_system_prompt(project, "inbound call")

    assistant_config = {
        "model": {
            "provider": "anthropic",
            "model": get_model_config(config),
            "temperature": 0.7,
            "messages": [{"role": "system", "content": system_prompt}]
        },
        "voice": get_voice_config(config),
        "firstMessage": f"Hey {user.get('name', 'there')}! I've got {project.get('name')} loaded up. What's on your mind?"
    }

    # Add tools if configured
    tool_ids = list(config.get("tool_ids", {}).values())
    if tool_ids:
        assistant_config["model"]["toolIds"] = tool_ids

    # Add language config for transcriber if set
    language = config.get("language")
    if language and language != "en":
        assistant_config["transcriber"] = {"provider": "deepgram", "language": language}

    return {"assistant": assistant_config}


def handle_end_of_call_report(data: dict) -> dict:
    """Handle call completion - auto-save transcript."""
    ensure_dirs()

    message = data.get("message", {})
    call = message.get("call", {})  # call is inside message

    transcript = message.get("transcript", "")
    summary = message.get("analysis", {}).get("summary", "") if message.get("analysis") else ""
    call_id = call.get("id", "unknown")
    duration = call.get("duration", 0)
    call_type = "Inbound" if call.get("type") == "inboundPhoneCall" else "Outbound"

    # Get project from metadata or default
    metadata = call.get("metadata", {})
    project_name = metadata.get("project")
    topic = metadata.get("topic", "general")

    # For inbound calls, try to get project from caller's config
    if not project_name and call_type == "Inbound":
        caller_phone = call.get("customer", {}).get("number", "")
        if caller_phone:
            config = load_config()
            user = config.get("users", {}).get(caller_phone)
            if user and user.get("last_project"):
                project_name = user.get("last_project")
            else:
                # Fall back to most recent project
                recent = get_most_recent_project()
                if recent:
                    project_name = recent.get("name")

    if not project_name:
        project_name = "unknown"

    print(f"[AUTO-SYNC] Call ended: {call_id[:8]}... ({call_type}, {duration}s)")

    if not transcript:
        print(f"[AUTO-SYNC] No transcript available")
        return {"status": "ok", "message": "no transcript"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{project_name}.md"
    filepath = TRANSCRIPTS_DIR / filename

    content = f"""# Call Transcript: {project_name}

**Date**: {datetime.now().isoformat()}
**Topic**: {topic}
**Duration**: {duration} seconds
**Type**: {call_type}
**Call ID**: {call_id}

## Transcript

{transcript}

## Summary

{summary if summary else 'No summary available'}

---
*Auto-synced by Claude Voice*
"""

    filepath.write_text(content)
    print(f"[AUTO-SYNC] Saved: {filepath}")

    return {"status": "ok", "transcript_path": str(filepath)}


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
        message_type = message.get("type")

        # Route based on message type
        if message_type == "assistant-request":
            response = handle_assistant_request(data)
            self.send_json(response)
            return

        if message_type == "end-of-call-report":
            response = handle_end_of_call_report(data)
            self.send_json(response)
            return

        if message_type == "tool-calls":
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
