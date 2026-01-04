# 🎙️ Claude Code Voice

> **Voice conversations with Claude about your code.**
> Have Claude call you to brainstorm, debug, or discuss your projects.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

When you're deep in a coding session and want to talk through a problem, run `/call` and Claude will call your phone with full context about what you're working on.

## What's Included

| Component | Description |
|-----------|-------------|
| **CLI Tool** | `claude-code-voice` command for setup, calls, and transcripts |
| **Claude Code Skill** | `/call` slash command integration |
| **Context Server** | Live file reading and code search during calls |
| **Transcripts** | Every call saved as markdown |

## Features

### Outbound Calls
Claude calls you, not the other way around. No waiting on hold.

```bash
claude-code-voice call "let's debug the auth flow"
claude-code-voice "brainstorm the new API design"
```

### Rich Context
Every call includes your project context automatically:
- Git status and recent commits
- Project type (Node.js, Python, Rust, Go, Swift, etc.)
- Recently modified files
- Current todos
- Claude Code session context (what you were just working on)

### Live Tools
During the call, Claude can:
- Read specific files from your project
- Search code patterns
- Get fresh context on demand

### Session Awareness
When used within Claude Code, the call inherits your session:
- What you've been working on
- Recent files touched
- Current problem or question

## Installation

```bash
pip install claude-code-voice
```

### As Claude Code Skill

```bash
ln -s /path/to/claude-code-voice ~/.claude/skills/call
```

Then use `/call` directly in conversations.

## Setup

```bash
claude-code-voice setup
```

You'll need:
1. [Vapi](https://vapi.ai) account and API key
2. Phone number in Vapi (purchased or imported from Twilio)
3. Your phone number

## Usage

### CLI Commands

```bash
claude-code-voice setup           # Configure credentials
claude-code-voice register        # Register current project
claude-code-voice call "topic"    # Have Claude call you
claude-code-voice sync            # Download transcripts
claude-code-voice history         # View past calls
claude-code-voice list            # List registered projects
claude-code-voice status          # Check configuration
claude-code-voice server          # Start context server
```

### Claude Code Skill

```
/call                        # Claude calls you
/call "debug the login bug"  # Call with specific topic
/call register               # Register current project
/call sync                   # Pull transcripts
```

## Context Server (Optional)

For live file access during calls:

```bash
# Terminal 1
claude-code-voice server

# Terminal 2
npx localtunnel --port 8765
```

## How It Works

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────┐
│  Claude Code    │────▶│    Vapi     │────▶│  Your Phone  │
│   (context)     │     │  (voice AI) │     │              │
└─────────────────┘     └──────┬──────┘     └──────────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │ Context Server  │
                      │  (live tools)   │
                      └─────────────────┘
```

1. **Register** captures project context
2. **Call** creates a transient Vapi assistant with full context
3. **Claude** converses naturally about your code
4. **Transcript** saved after call ends

## Configuration

Stored in `~/.claude-code-voice/config.json` (or `~/.claude/skills/call/data/` as a skill).

## License

MIT
