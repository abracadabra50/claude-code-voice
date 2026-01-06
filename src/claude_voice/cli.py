#!/usr/bin/env python3
"""
Claude Code Voice CLI
Talk to Claude about your projects over the phone.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests package not installed")
    print("Run: pip install requests")
    sys.exit(1)

# Config paths - use ~/.claude-code-voice for standalone, ~/.claude/skills/call for skill mode
def get_data_dir() -> Path:
    """Get the data directory, checking for skill mode first."""
    skill_dir = Path.home() / ".claude" / "skills" / "call" / "data"
    if skill_dir.exists():
        return skill_dir

    data_dir = Path.home() / ".claude-code-voice"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DATA_DIR = get_data_dir()
CONFIG_FILE = DATA_DIR / "config.json"
PROJECTS_DIR = DATA_DIR / "projects"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"

# Vapi API
VAPI_API_URL = "https://api.vapi.ai"


def ensure_dirs():
    """Ensure all required directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load configuration."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config: dict):
    """Save configuration."""
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_vapi_key() -> str:
    """Get Vapi API key from config or environment."""
    config = load_config()
    key = os.environ.get("VAPI_API_KEY") or config.get("vapi_api_key")
    if not key:
        print("ERROR: No Vapi API key configured")
        print("Run: claude-code-voice setup")
        sys.exit(1)
    return key


def vapi_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make a request to Vapi API."""
    key = get_vapi_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    url = f"{VAPI_API_URL}{endpoint}"

    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method == "PATCH":
        response = requests.patch(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unknown method: {method}")

    if response.status_code >= 400:
        print(f"ERROR: Vapi API error {response.status_code}")
        print(response.text)
        sys.exit(1)

    return response.json()


# ============================================================================
# SETUP COMMAND
# ============================================================================

def cmd_setup(args):
    """Configure Vapi credentials and phone number."""
    print("=" * 50)
    print("  Claude Voice Setup")
    print("=" * 50)
    print()
    print("Before you start, you'll need:")
    print("  1. Vapi account: https://vapi.ai (free to sign up)")
    print("  2. Vapi API key: https://dashboard.vapi.ai/api-keys")
    print("  3. Vapi phone number: https://dashboard.vapi.ai/phone-numbers")
    print("     (Click 'Buy Number' - costs ~$2/month)")
    print()

    config = load_config()

    # Get API key
    if args.api_key:
        api_key = args.api_key
    else:
        api_key = input("Vapi API Key: ").strip()

    if not api_key:
        print("ERROR: API key required")
        sys.exit(1)

    config["vapi_api_key"] = api_key

    # Get phone number
    if args.phone:
        phone = args.phone
    else:
        phone = input("Your phone number (e.g., +14155551234): ").strip()

    if not phone.startswith("+"):
        phone = "+" + phone

    config["user_phone"] = phone

    # Get user's name (optional)
    if args.name:
        user_name = args.name
    else:
        user_name = input("Your name (for personalized greetings, or press Enter to skip): ").strip()

    if not user_name:
        user_name = "there"  # Fallback for "Hey there!"

    config["user_name"] = user_name

    # Also add to users dict for inbound call recognition
    if "users" not in config:
        config["users"] = {}
    config["users"][phone] = {"name": user_name, "last_project": None}

    save_config(config)
    print(f"\n✅ Config saved to {CONFIG_FILE}")

    # Verify API key and get phone numbers
    print("\nVerifying API key...")
    try:
        os.environ["VAPI_API_KEY"] = api_key
        phone_numbers = vapi_request("GET", "/phone-number")
        print(f"✅ API key valid. Found {len(phone_numbers)} phone number(s).")

        if phone_numbers:
            print("\nAvailable phone numbers:")
            for i, pn in enumerate(phone_numbers):
                print(f"  {i+1}. {pn.get('number', 'N/A')} (ID: {pn.get('id', 'N/A')[:8]}...)")

            # Let user pick
            if len(phone_numbers) == 1:
                choice = 0
            else:
                choice_str = input(f"\nSelect phone number [1-{len(phone_numbers)}]: ").strip()
                choice = int(choice_str) - 1 if choice_str else 0

            config["vapi_phone_number_id"] = phone_numbers[choice]["id"]
            config["vapi_phone_number"] = phone_numbers[choice].get("number", "")
            save_config(config)
            print(f"\n✅ Using phone number: {config['vapi_phone_number']}")
        else:
            print("\n⚠️  No phone numbers found. Create one in Vapi dashboard.")
            print("   https://dashboard.vapi.ai/phone-numbers")
    except Exception as e:
        print(f"⚠️  Could not verify API key: {e}")

    # Create tools
    print("\nSetting up voice tools...")
    try:
        tool_ids = create_tools(config)
        config["tool_ids"] = tool_ids
        save_config(config)
        print(f"✅ Created {len(tool_ids)} tools")
    except Exception as e:
        print(f"⚠️  Could not create tools: {e}")

    print("\n" + "=" * 50)
    print("  Setup Complete!")
    print("=" * 50)
    print(f"\n  Your name:   {config.get('user_name', 'Not set')}")
    print(f"  Your phone:  {config.get('user_phone', 'Not set')}")
    print(f"  Vapi number: {config.get('vapi_phone_number', 'Not set')}")
    print("\nNext steps:")
    print("  1. cd into a project directory")
    print("  2. Run: claude-code-voice register")
    print("  3. Run: claude-code-voice start")
    print("\nThen you can:")
    print("  - Have Claude call you: claude-code-voice call")
    print(f"  - Call Claude: dial {config.get('vapi_phone_number', 'your Vapi number')}")


def create_tools(config: dict) -> dict:
    """Create Vapi tools for live context fetching."""
    tools = {
        "get_project_context": {
            "type": "function",
            "function": {
                "name": "get_project_context",
                "description": "Get overview of a project including git status, todos, recent files",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Name of the project"}
                    },
                    "required": ["project_name"]
                }
            },
            "server": {"url": config.get("server_url", "https://placeholder.example.com")}
        },
        "read_file": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read contents of a specific file from the project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Name of the project"},
                        "file_path": {"type": "string", "description": "Relative path to the file"}
                    },
                    "required": ["project_name", "file_path"]
                }
            },
            "server": {"url": config.get("server_url", "https://placeholder.example.com")}
        },
        "search_code": {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": "Search for code patterns or text in the project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Name of the project"},
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["project_name", "query"]
                }
            },
            "server": {"url": config.get("server_url", "https://placeholder.example.com")}
        },
        "list_projects": {
            "type": "function",
            "function": {
                "name": "list_projects",
                "description": "List all registered projects",
                "parameters": {"type": "object", "properties": {}}
            },
            "server": {"url": config.get("server_url", "https://placeholder.example.com")}
        }
    }

    tool_ids = {}
    for name, tool_data in tools.items():
        result = vapi_request("POST", "/tool", tool_data)
        tool_ids[name] = result["id"]

    return tool_ids


# ============================================================================
# REGISTER COMMAND
# ============================================================================

def cmd_register(args):
    """Register current project for voice calls."""
    config = load_config()

    if not config.get("vapi_api_key"):
        print("Note: Vapi not configured yet. Run 'claude-voice setup' before making calls.\n")

    cwd = Path.cwd()
    project_name = args.name or cwd.name

    print(f"=== Registering Project: {project_name} ===\n")

    context = gather_project_context(cwd)

    project_data = {
        "name": project_name,
        "path": str(cwd),
        "aliases": [project_name.lower(), project_name.replace("-", " ").lower()],
        "registered_at": datetime.now().isoformat(),
        "last_context_update": datetime.now().isoformat(),
        "context": context
    }

    ensure_dirs()
    project_file = PROJECTS_DIR / f"{project_name}.json"
    with open(project_file, "w") as f:
        json.dump(project_data, f, indent=2)

    print(f"Project: {project_name}")
    print(f"Path: {cwd}")
    print(f"Description: {context.get('description', 'N/A')[:100]}")
    print(f"Type: {context.get('project_type', 'Unknown')}")
    print(f"Git status: {context.get('git_summary', 'N/A')}")
    print(f"Todos: {len(context.get('todos', []))} items")
    print(f"Recent files: {len(context.get('recent_files', []))} files")

    print(f"\n✅ Project registered: {project_file}")
    print(f"\nYou can now run 'claude-code-voice call' to have Claude call you.")


def gather_project_context(project_path: Path) -> dict:
    """Gather context about a project."""
    context = {
        "description": "",
        "project_type": "Unknown",
        "git_summary": "",
        "todos": [],
        "recent_files": [],
        "recent_commits": []
    }

    # Try to get description from README
    for readme in ["README.md", "README.txt", "README"]:
        readme_path = project_path / readme
        if readme_path.exists():
            content = readme_path.read_text()[:1000]
            lines = content.split("\n\n")[0].split("\n")
            context["description"] = " ".join(l.strip("#").strip() for l in lines if l.strip())[:200]
            break

    # Detect project type
    if (project_path / "package.json").exists():
        context["project_type"] = "Node.js"
        try:
            pkg = json.loads((project_path / "package.json").read_text())
            if not context["description"]:
                context["description"] = pkg.get("description", "")
        except:
            pass
    elif (project_path / "requirements.txt").exists() or (project_path / "pyproject.toml").exists():
        context["project_type"] = "Python"
    elif (project_path / "Cargo.toml").exists():
        context["project_type"] = "Rust"
    elif (project_path / "go.mod").exists():
        context["project_type"] = "Go"
    elif (project_path / "Package.swift").exists():
        context["project_type"] = "Swift"

    # Git status
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            modified = len([l for l in lines if l.startswith(" M") or l.startswith("M ")])
            added = len([l for l in lines if l.startswith("A ") or l.startswith("??")])
            context["git_summary"] = f"{modified} modified, {added} untracked"
    except:
        pass

    # Recent commits
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=project_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            context["recent_commits"] = result.stdout.strip().split("\n")
    except:
        pass

    # Recent files
    try:
        result = subprocess.run(
            ["find", ".", "-maxdepth", "2", "-type", "f", "-name", "*.py", "-o",
             "-name", "*.ts", "-o", "-name", "*.js", "-o", "-name", "*.swift"],
            cwd=project_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            files = result.stdout.strip().split("\n")[:20]
            context["recent_files"] = [f for f in files if f]
    except:
        pass

    # Look for todos
    todo_files = [".todos.json", "TODO.md", ".claude/todos.json"]
    for tf in todo_files:
        todo_path = project_path / tf
        if todo_path.exists():
            try:
                if tf.endswith(".json"):
                    todos = json.loads(todo_path.read_text())
                    context["todos"] = todos if isinstance(todos, list) else []
                else:
                    content = todo_path.read_text()
                    context["todos"] = [
                        line.strip("- [ ]").strip()
                        for line in content.split("\n")
                        if line.strip().startswith("- [ ]")
                    ][:10]
            except:
                pass
            break

    return context


# ============================================================================
# CALL COMMAND
# ============================================================================

def cmd_call(args):
    """Make an outbound call with rich context."""
    config = load_config()

    if not config.get("vapi_api_key"):
        print("ERROR: Run 'claude-code-voice setup' first")
        sys.exit(1)

    if not config.get("user_phone"):
        print("ERROR: No phone number configured. Run 'claude-code-voice setup'")
        sys.exit(1)

    if not config.get("vapi_phone_number_id"):
        print("ERROR: No Vapi phone number configured. Run 'claude-code-voice setup'")
        sys.exit(1)

    cwd = Path.cwd()
    project = find_project(cwd)

    if not project:
        print(f"⚠️  Project not registered. Registering {cwd.name}...")
        class FakeArgs:
            name = None
        cmd_register(FakeArgs())
        project = find_project(cwd)

    topic = args.topic if args.topic else "general check-in"

    # Refresh project context
    project["context"] = gather_project_context(Path(project["path"]))
    project["last_context_update"] = datetime.now().isoformat()

    ensure_dirs()
    project_file = PROJECTS_DIR / f"{project['name']}.json"
    with open(project_file, "w") as f:
        json.dump(project, f, indent=2)

    context = project["context"]

    # Check for session context file (written by Claude Code before calling)
    session_context = ""
    session_file = Path("/tmp/claude_code_session_context.json")
    if session_file.exists():
        try:
            session_data = json.loads(session_file.read_text())
            session_context = f"""

CURRENT CLAUDE CODE SESSION:
What we've been working on: {session_data.get('current_task', 'General discussion')}
Recent files touched: {', '.join(session_data.get('recent_files', [])[:5])}
Current problem/question: {session_data.get('current_problem', 'None specified')}
Session notes: {session_data.get('notes', '')}
"""
            session_file.unlink()
        except:
            pass

    # Build rich system prompt
    system_prompt = f"""You are Claude, a technical co-pilot having a phone conversation with a developer.

PERSONALITY:
- Warm, friendly, conversational - like a colleague on a call
- Keep responses SHORT - 1-2 sentences usually. This is voice, not text.
- Technical but explains in plain language when needed
- Proactive - suggest ideas, spot issues, help brainstorm

PROJECT: {project['name']}
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
{session_context}
DISCUSSION TOPIC: {topic}

You have tools available to:
- list_projects: See all registered projects
- get_project_context: Get fresh context for any project
- read_file: Read a specific file (summarize for voice)
- search_code: Search for code patterns

Use tools when you need LIVE data. The context above is a snapshot.
Keep responses brief and conversational. Ask clarifying questions. Help brainstorm."""

    first_message = "Hey! "
    if topic != "general check-in":
        first_message += f"You wanted to discuss {topic}. "
    first_message += "What's on your mind?"

    print(f"📞 Calling {config['user_phone']}...")
    print(f"   Project: {project['name']}")
    print(f"   Topic: {topic}")
    if session_context:
        print(f"   Session context: ✅ loaded")

    # Use transient assistant with rich context
    voice_provider = config.get("voice_provider", "openai")
    voice_id = config.get("voice_id", "alloy")
    model_name = config.get("model", "claude-opus-4-5-20251101")

    assistant_config = {
        "model": {
            "provider": "anthropic",
            "model": model_name,
            "temperature": 0.7,
            "messages": [{"role": "system", "content": system_prompt}],
        },
        "voice": {"provider": voice_provider, "voiceId": voice_id},
        "firstMessage": first_message,
    }

    # Only include toolIds if tools are configured
    tool_ids = list(config.get("tool_ids", {}).values())
    if tool_ids:
        assistant_config["model"]["toolIds"] = tool_ids

    # Only include serverUrl if actually configured (Vapi rejects empty string)
    server_url = config.get("server_url")
    if server_url:
        assistant_config["serverUrl"] = server_url

    # Add language config for transcriber if set
    language = config.get("language")
    if language and language != "en":
        assistant_config["transcriber"] = {"provider": "deepgram", "language": language}

    call_data = {
        "phoneNumberId": config["vapi_phone_number_id"],
        "customer": {"number": config["user_phone"]},
        "assistant": assistant_config,
        "metadata": {
            "project": project["name"],
            "topic": topic
        }
    }

    try:
        result = vapi_request("POST", "/call", call_data)
        print(f"\n✅ Call initiated!")
        print(f"   Call ID: {result.get('id', 'N/A')}")
        print(f"   Status: {result.get('status', 'N/A')}")

        # Save call info for transcript sync
        call_record = {
            "call_id": result.get("id"),
            "project": project["name"],
            "topic": topic,
            "started_at": datetime.now().isoformat(),
            "status": result.get("status")
        }

        calls_file = DATA_DIR / "pending_calls.json"
        pending = []
        if calls_file.exists():
            pending = json.loads(calls_file.read_text())
        pending.append(call_record)
        calls_file.write_text(json.dumps(pending, indent=2))

    except Exception as e:
        print(f"❌ Failed to make call: {e}")
        sys.exit(1)


def find_project(path: Path) -> Optional[dict]:
    """Find a registered project by path."""
    for project_file in PROJECTS_DIR.glob("*.json"):
        try:
            project = json.loads(project_file.read_text())
            if Path(project.get("path", "")) == path:
                return project
        except:
            pass
    return None


# ============================================================================
# SYNC COMMAND
# ============================================================================

def cmd_sync(args):
    """Sync transcripts from completed calls."""
    config = load_config()

    if not config.get("vapi_api_key"):
        print("ERROR: Run 'claude-code-voice setup' first")
        sys.exit(1)

    print("=== Syncing Call Transcripts ===\n")

    calls_file = DATA_DIR / "pending_calls.json"
    if not calls_file.exists():
        print("No pending calls to sync.")
        return

    pending = json.loads(calls_file.read_text())
    if not pending:
        print("No pending calls to sync.")
        return

    synced = []
    still_pending = []

    for call in pending:
        call_id = call.get("call_id")
        if not call_id:
            continue

        print(f"Checking call {call_id[:8]}...")

        try:
            result = vapi_request("GET", f"/call/{call_id}")
            status = result.get("status")

            if status == "ended":
                transcript = result.get("transcript", "")
                summary = result.get("summary", "")
                duration = result.get("duration", 0)

                if transcript:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{call['project']}.md"
                    filepath = TRANSCRIPTS_DIR / filename

                    content = f"""# Call Transcript: {call['project']}

**Date**: {call.get('started_at', 'Unknown')}
**Topic**: {call.get('topic', 'General')}
**Duration**: {duration} seconds

## Transcript

{transcript}

## Summary

{summary if summary else 'No summary available'}

---
*Synced at {datetime.now().isoformat()}*
"""
                    filepath.write_text(content)
                    print(f"  ✅ Saved: {filepath}")
                    synced.append(call)
                else:
                    print(f"  ⚠️  No transcript available")
                    synced.append(call)

            elif status in ["queued", "ringing", "in-progress"]:
                print(f"  ⏳ Still in progress ({status})")
                still_pending.append(call)
            else:
                print(f"  ❌ Call failed or cancelled ({status})")
                synced.append(call)

        except Exception as e:
            print(f"  ❌ Error checking call: {e}")
            still_pending.append(call)

    calls_file.write_text(json.dumps(still_pending, indent=2))

    print(f"\n✅ Synced {len(synced)} calls")
    if still_pending:
        print(f"⏳ {len(still_pending)} calls still pending")


# ============================================================================
# OTHER COMMANDS
# ============================================================================

def cmd_history(args):
    """Show call history."""
    print("=== Call History ===\n")

    transcripts = sorted(TRANSCRIPTS_DIR.glob("*.md"), reverse=True)

    if not transcripts:
        print("No calls yet.")
        return

    limit = args.limit or 10

    for i, t in enumerate(transcripts[:limit]):
        name = t.stem
        parts = name.split("_", 2)
        if len(parts) >= 3:
            date = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:8]}"
            time = f"{parts[1][:2]}:{parts[1][2:4]}"
            project = parts[2]
        else:
            date, time, project = "Unknown", "", name

        print(f"{i+1}. [{date} {time}] {project}")
        print(f"   {t}")

    if len(transcripts) > limit:
        print(f"\n... and {len(transcripts) - limit} more")


def cmd_list(args):
    """List registered projects."""
    print("=== Registered Projects ===\n")

    projects = list(PROJECTS_DIR.glob("*.json"))

    if not projects:
        print("No projects registered.")
        print("Run 'claude-code-voice register' in a project directory.")
        return

    for pf in projects:
        try:
            project = json.loads(pf.read_text())
            name = project.get("name", pf.stem)
            path = project.get("path", "Unknown")
            registered = project.get("registered_at", "Unknown")[:10]
            print(f"• {name}")
            print(f"  Path: {path}")
            print(f"  Registered: {registered}")
            print()
        except:
            print(f"• {pf.stem} (error reading)")


def cmd_status(args):
    """Show skill status."""
    print("=== Claude Voice Status ===\n")

    config = load_config()

    print("Configuration:")
    print(f"  API Key: {'✅ Set' if config.get('vapi_api_key') else '❌ Not set'}")
    print(f"  Your Phone: {config.get('user_phone', '❌ Not set')}")
    print(f"  Vapi Number: {config.get('vapi_phone_number', '❌ Not set')}")
    print(f"  Server URL: {config.get('server_url', '❌ Not set')}")
    print(f"  Tools: {len(config.get('tool_ids', {}))} configured")

    projects = list(PROJECTS_DIR.glob("*.json"))
    print(f"\nProjects: {len(projects)} registered")

    transcripts = list(TRANSCRIPTS_DIR.glob("*.md"))
    print(f"Transcripts: {len(transcripts)} calls")

    calls_file = DATA_DIR / "pending_calls.json"
    if calls_file.exists():
        pending = json.loads(calls_file.read_text())
        print(f"Pending sync: {len(pending)} calls")


def cmd_server(args):
    """Start the context server."""
    from .server import main as server_main
    server_main(args)


def cmd_start(args):
    """Start server + tunnel and configure everything automatically."""
    import time
    import signal
    import re

    config = load_config()

    if not config.get("vapi_api_key"):
        print("ERROR: Run 'claude-code-voice setup' first")
        sys.exit(1)

    port = args.port

    print("🚀 Starting Claude Voice...")
    print(f"   Port: {port}")

    # Kill any existing processes on the port
    try:
        subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null", shell=True, capture_output=True)
        time.sleep(1)
    except:
        pass

    # Start server in background
    print("\n📡 Starting context server...")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "claude_voice.server", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    time.sleep(2)

    if server_proc.poll() is not None:
        print("❌ Server failed to start")
        sys.exit(1)
    print(f"   ✅ Server running on port {port}")

    # Start tunnel
    print("\n🌐 Starting tunnel...")
    tunnel_proc = subprocess.Popen(
        ["npx", "localtunnel", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Wait for tunnel URL
    tunnel_url = None
    for _ in range(30):  # 30 second timeout
        line = tunnel_proc.stdout.readline()
        if "your url is:" in line.lower():
            match = re.search(r'https://[^\s]+', line)
            if match:
                tunnel_url = match.group(0)
                break
        time.sleep(0.5)

    if not tunnel_url:
        print("❌ Tunnel failed to start")
        server_proc.terminate()
        sys.exit(1)

    print(f"   ✅ Tunnel: {tunnel_url}")

    # Configure server URL
    print("\n⚙️  Configuring Vapi...")
    config["server_url"] = tunnel_url
    save_config(config)

    # Update tools
    tool_ids = config.get("tool_ids", {})
    if tool_ids:
        updated = 0
        for tool_name, tool_id in tool_ids.items():
            try:
                vapi_request("PATCH", f"/tool/{tool_id}", {"server": {"url": tunnel_url}})
                updated += 1
            except:
                pass
        print(f"   ✅ Updated {updated} tools")

    # Configure inbound calls
    phone_id = config.get("vapi_phone_number_id")
    if phone_id:
        try:
            vapi_request("PATCH", f"/phone-number/{phone_id}", {
                "serverUrl": tunnel_url,
                "assistantId": None
            })
            print(f"   ✅ Inbound calls configured")
        except Exception as e:
            print(f"   ⚠️  Could not configure inbound: {e}")

    # Summary
    print("\n" + "=" * 50)
    print("✅ Claude Voice is ready!")
    print("=" * 50)
    print(f"\n📞 Outbound: Run 'claude-code-voice call' to have Claude call you")
    print(f"📲 Inbound:  Call {config.get('vapi_phone_number', 'your Vapi number')}")
    print(f"\n💡 Keep this terminal open to receive calls")
    print("   Press Ctrl+C to stop\n")

    # Handle Ctrl+C gracefully
    def cleanup(sig, frame):
        print("\n\n👋 Shutting down...")
        server_proc.terminate()
        tunnel_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    # Keep running and show logs
    try:
        while True:
            # Read from server
            if server_proc.stdout:
                line = server_proc.stdout.readline()
                if line:
                    print(line.decode().strip())
            time.sleep(0.1)
    except KeyboardInterrupt:
        cleanup(None, None)


def cmd_config(args):
    """Set or get configuration values."""
    config = load_config()

    if args.key == "server-url":
        if args.value:
            # Setting a value
            url = args.value.strip()
            if url and not url.startswith("https://"):
                print("WARNING: Server URL should use HTTPS for Vapi to connect")
            config["server_url"] = url
            save_config(config)
            print(f"✅ server_url = {url}")

            # Update existing tools with new URL
            tool_ids = config.get("tool_ids", {})
            if tool_ids and config.get("vapi_api_key"):
                print("\nUpdating tools with new server URL...")
                updated = 0
                for tool_name, tool_id in tool_ids.items():
                    try:
                        vapi_request("PATCH", f"/tool/{tool_id}", {
                            "server": {"url": url}
                        })
                        updated += 1
                    except Exception as e:
                        print(f"  ⚠️  Failed to update {tool_name}: {e}")
                print(f"✅ Updated {updated}/{len(tool_ids)} tools")
            elif not tool_ids:
                print("\nNo tools configured yet. Run 'claude-code-voice setup' first.")
        else:
            # Getting a value
            value = config.get("server_url", "")
            if value:
                print(f"server_url = {value}")
            else:
                print("server_url is not set")
                print("\nTo set it, run your context server and tunnel, then:")
                print("  claude-code-voice config server-url https://your-tunnel-url.loca.lt")

    elif args.key == "name":
        if args.value:
            # Setting name
            name = args.value.strip()
            config["user_name"] = name

            # Also update in users dict
            user_phone = config.get("user_phone")
            if user_phone:
                if "users" not in config:
                    config["users"] = {}
                if user_phone in config["users"]:
                    config["users"][user_phone]["name"] = name
                else:
                    config["users"][user_phone] = {"name": name, "last_project": None}

            save_config(config)
            print(f"✅ name = {name}")
            print(f"\nClaude will now greet you as: \"Hey {name}!\"")
        else:
            # Getting name
            name = config.get("user_name", "")
            if name:
                print(f"name = {name}")
            else:
                print("name is not set")
                print("\nTo set it, run:")
                print("  claude-code-voice config name YourName")

    elif args.key == "voice":
        if args.value:
            # Parse voice format: provider:voiceId (e.g., elevenlabs:rachel, openai:nova)
            voice = args.value.strip()
            if ":" in voice:
                provider, voice_id = voice.split(":", 1)
            else:
                # Default to openai if no provider specified
                provider = "openai"
                voice_id = voice

            # Validate provider
            valid_providers = ["openai", "elevenlabs", "deepgram", "playht", "azure"]
            if provider not in valid_providers:
                print(f"⚠️  Unknown provider: {provider}")
                print(f"   Valid providers: {', '.join(valid_providers)}")
                return

            config["voice_provider"] = provider
            config["voice_id"] = voice_id
            save_config(config)
            print(f"✅ voice = {provider}:{voice_id}")
            print(f"\nVoice options:")
            print(f"  OpenAI: alloy, echo, fable, onyx, nova, shimmer")
            print(f"  ElevenLabs: Use voice ID from elevenlabs.io")
        else:
            provider = config.get("voice_provider", "openai")
            voice_id = config.get("voice_id", "alloy")
            print(f"voice = {provider}:{voice_id}")
            print(f"\nTo change: claude-code-voice config voice provider:voiceId")
            print(f"Examples:")
            print(f"  claude-code-voice config voice openai:nova")
            print(f"  claude-code-voice config voice elevenlabs:YOUR_VOICE_ID")

    elif args.key == "model":
        if args.value:
            model = args.value.strip().lower()
            model_map = {
                "opus": "claude-opus-4-5-20251101",
                "sonnet": "claude-sonnet-4-20250514",
                "opus-4.5": "claude-opus-4-5-20251101",
                "sonnet-4": "claude-sonnet-4-20250514",
            }
            if model in model_map:
                config["model"] = model_map[model]
                save_config(config)
                print(f"✅ model = {model_map[model]}")
            elif model.startswith("claude-"):
                config["model"] = model
                save_config(config)
                print(f"✅ model = {model}")
            else:
                print(f"⚠️  Unknown model: {model}")
                print(f"   Use: opus, sonnet, or full model ID")
        else:
            model = config.get("model", "claude-opus-4-5-20251101")
            print(f"model = {model}")
            print(f"\nTo change: claude-code-voice config model opus|sonnet")

    elif args.key == "language":
        if args.value:
            lang = args.value.strip()
            config["language"] = lang
            save_config(config)
            print(f"✅ language = {lang}")
            print(f"\nClaude will now speak in {lang}")
        else:
            lang = config.get("language", "en")
            print(f"language = {lang}")
            print(f"\nTo change: claude-code-voice config language es|fr|de|etc")

    elif args.key == "show":
        print("=== Configuration ===\n")
        for key, value in config.items():
            if key == "vapi_api_key":
                print(f"  {key}: ***{value[-4:] if value else 'Not set'}")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"Unknown config key: {args.key}")
        print("\nAvailable keys:")
        print("  server-url  - URL of your context server")
        print("  name        - Your name for greetings")
        print("  voice       - Voice provider:id (e.g., elevenlabs:rachel)")
        print("  model       - AI model (opus, sonnet)")
        print("  language    - Language code (en, es, fr, de)")
        print("  show        - Show all configuration")


# ============================================================================
# CONFIGURE INBOUND COMMAND
# ============================================================================

def cmd_configure_inbound(args):
    """Configure Vapi phone number for inbound calls."""
    config = load_config()

    if not config.get("vapi_api_key"):
        print("ERROR: Run 'claude-code-voice setup' first")
        sys.exit(1)

    if not config.get("vapi_phone_number_id"):
        print("ERROR: No Vapi phone number configured. Run 'claude-code-voice setup'")
        sys.exit(1)

    server_url = config.get("server_url")
    if not server_url:
        print("ERROR: Server URL not configured")
        print("\nFor inbound calls, you need to run your context server and tunnel:")
        print("  1. Terminal 1: claude-code-voice server")
        print("  2. Terminal 2: npx localtunnel --port 8765")
        print("  3. Then run: claude-code-voice config server-url <your-tunnel-url>")
        print("  4. Finally run: claude-code-voice configure-inbound")
        sys.exit(1)

    print("=== Configuring Inbound Calls ===\n")

    phone_id = config["vapi_phone_number_id"]
    phone_number = config.get("vapi_phone_number", "Unknown")

    print(f"Phone: {phone_number}")
    print(f"Server URL: {server_url}")

    # PATCH the phone number to use server URL for inbound
    try:
        vapi_request("PATCH", f"/phone-number/{phone_id}", {
            "serverUrl": server_url,
            "assistantId": None  # Clear any fixed assistant - we use dynamic
        })
        print(f"\n✅ Inbound calls configured!")
        print(f"\nWhen someone calls {phone_number}, Vapi will:")
        print(f"  1. Send assistant-request webhook to {server_url}")
        print(f"  2. Your server returns dynamic assistant based on caller")
        print(f"  3. Claude answers with caller's project context")
    except Exception as e:
        print(f"❌ Failed to configure: {e}")
        sys.exit(1)

    # Ensure user is registered
    user_phone = config.get("user_phone")
    if user_phone:
        users = config.get("users", {})
        if user_phone not in users:
            users[user_phone] = {"name": "User", "last_project": None}
            config["users"] = users
            save_config(config)
            print(f"\n📱 Registered {user_phone} for caller recognition")

    print(f"\nNOTE: Keep your server + tunnel running to receive inbound calls!")


# ============================================================================
# MAIN
# ============================================================================

COMMANDS = {"setup", "register", "call", "sync", "history", "list", "status", "server", "start", "config", "configure-inbound"}


def main():
    # Handle slash-command style: /call "topic" -> claude-code-voice "topic"
    # If first arg is not a known command, treat it as a call topic
    if len(sys.argv) > 1 and sys.argv[1] not in COMMANDS and not sys.argv[1].startswith("-"):
        # Treat all args as call topic
        topic = " ".join(sys.argv[1:])
        sys.argv = [sys.argv[0], "call", topic]

    parser = argparse.ArgumentParser(
        description="Claude Code Voice - Talk to Claude about your projects over the phone"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Setup
    setup_parser = subparsers.add_parser("setup", help="Configure Vapi credentials")
    setup_parser.add_argument("--api-key", help="Vapi API key")
    setup_parser.add_argument("--phone", help="Your phone number")
    setup_parser.add_argument("--name", help="Your name (for personalized greetings)")

    # Register
    register_parser = subparsers.add_parser("register", help="Register current project")
    register_parser.add_argument("--name", help="Project name (default: directory name)")

    # Call
    call_parser = subparsers.add_parser("call", help="Make an outbound call")
    call_parser.add_argument("topic", nargs="*", help="Topic to discuss")

    # Sync
    subparsers.add_parser("sync", help="Sync transcripts")

    # History
    history_parser = subparsers.add_parser("history", help="Show call history")
    history_parser.add_argument("--limit", "-n", type=int, default=10)

    # List
    subparsers.add_parser("list", help="List registered projects")

    # Status
    subparsers.add_parser("status", help="Show skill status")

    # Server
    server_parser = subparsers.add_parser("server", help="Start context server")
    server_parser.add_argument("--port", type=int, default=8765)

    # Start (all-in-one)
    start_parser = subparsers.add_parser("start", help="Start server + tunnel (easy mode)")
    start_parser.add_argument("--port", type=int, default=8765)

    # Config
    config_parser = subparsers.add_parser("config", help="Set or get configuration values")
    config_parser.add_argument("key", help="Config key (server-url, show)")
    config_parser.add_argument("value", nargs="?", help="Value to set (omit to get current value)")

    # Configure Inbound
    subparsers.add_parser("configure-inbound", help="Configure phone number for inbound calls")

    args = parser.parse_args()

    ensure_dirs()

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "register":
        cmd_register(args)
    elif args.command == "call":
        args.topic = " ".join(args.topic) if args.topic else None
        cmd_call(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "server":
        cmd_server(args)
    elif args.command == "start":
        cmd_start(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "configure-inbound":
        cmd_configure_inbound(args)
    else:
        # No command = make a call
        class FakeArgs:
            topic = None
        cmd_call(FakeArgs())


if __name__ == "__main__":
    main()
