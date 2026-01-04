# Claude Voice

Talk to Claude about your projects over the phone.

A Claude Code skill that enables voice conversations about your codebase. Call a dedicated phone number to brainstorm, get updates, or discuss your code with an AI that knows your project context.

## Features

- **Outbound calls** - `/call` triggers Claude to call you
- **Rich context** - Claude knows your git status, todos, recent files, and current session
- **Live tools** - Can read files and search code during the call
- **Transcripts** - All calls saved as markdown for later reference

## Quick Start

```bash
# 1. Install
pip install claude-voice

# 2. Configure (needs Vapi account)
claude-voice setup

# 3. Register your project
cd your-project
claude-voice register

# 4. Make a call
claude-voice call "discuss the auth flow"
```

## Requirements

- Python 3.8+
- [Vapi](https://vapi.ai) account (handles voice AI)
- Phone number in Vapi (for outbound calls)

## Installation

### From PyPI (coming soon)
```bash
pip install claude-voice
```

### From source
```bash
git clone https://github.com/abracadabra50/claude-voice.git
cd claude-voice
pip install -e .
```

### As Claude Code Skill
```bash
# Copy to skills directory
cp -r claude-voice ~/.claude/skills/call

# Or symlink
ln -s $(pwd) ~/.claude/skills/call
```

## Commands

| Command | Description |
|---------|-------------|
| `setup` | Configure Vapi API key and phone number |
| `register` | Register current project for voice calls |
| `call [topic]` | Claude calls you about this project |
| `sync` | Pull transcripts from completed calls |
| `history` | Show recent call history |
| `list` | List registered projects |
| `status` | Show configuration status |
| `server` | Start the context server (for live tools) |

## Usage

### First-time Setup

```bash
claude-voice setup
```

You'll need:
1. Vapi API key from https://dashboard.vapi.ai
2. A phone number purchased in Vapi
3. Your phone number (where Claude calls you)

### Register a Project

```bash
cd ~/my-project
claude-voice register
```

This captures:
- Project type (Node.js, Python, etc.)
- Description from README
- Git status
- Recent files
- Current todos

### Make a Call

```bash
# General check-in
claude-voice call

# Specific topic
claude-voice call "brainstorm the new feature"
claude-voice call "debug the auth issue"
```

### With Claude Code

When used as a Claude Code skill:

```
/call                    # Claude calls you
/call "discuss auth"     # With specific topic
/call register           # Register current project
/call sync               # Pull transcripts
```

## Context Server (Optional)

For live file reading and code search during calls:

```bash
# Terminal 1: Start server
claude-voice server

# Terminal 2: Expose with tunnel (pick one)
npx localtunnel --port 8765
# or
ngrok http 8765
```

Then update your config with the tunnel URL.

## Configuration

Config stored in `~/.claude-voice/config.json`:

```json
{
  "vapi_api_key": "your-key",
  "vapi_phone_number_id": "phone-id",
  "vapi_phone_number": "+1234567890",
  "user_phone": "+0987654321",
  "server_url": "https://your-tunnel.loca.lt"
}
```

## How It Works

1. **Registration** captures project context (git, files, todos)
2. **Call** creates a transient Vapi assistant with:
   - Rich context baked into system prompt (fast)
   - Tools for live lookups (when needed)
3. **Voice Claude** converses naturally about your project
4. **Transcript** saved after call ends

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────┐
│  Claude Code    │────▶│    Vapi     │────▶│  Your Phone  │
│  (context)      │     │  (voice AI) │     │              │
└─────────────────┘     └──────┬──────┘     └──────────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │ Context Server  │
                      │ (live tools)    │
                      └─────────────────┘
```

## License

MIT

## Credits

Built with [Vapi](https://vapi.ai) for voice AI and [Claude](https://anthropic.com) for the brains.
