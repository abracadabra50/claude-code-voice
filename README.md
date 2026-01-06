# Claude Code Voice

> **Voice conversations with Claude Opus 4.5 about your code.**

Talk through problems, brainstorm ideas, or get a code review — all over the phone.

## Quick Start

```bash
# Install
pip install claude-code-voice

# One-time setup
claude-code-voice setup

# Register a project
cd your-project
claude-code-voice register

# Start everything (server + tunnel + config)
claude-code-voice start
```

That's it! Now you can:
- **Have Claude call you**: `claude-code-voice call "debug the auth flow"`
- **Call Claude**: Dial your Vapi number and Claude answers with your project loaded

## What You Need

Before running setup:
1. **Vapi account** — https://vapi.ai (free to sign up, **$10 credit included**)
2. **Vapi API key** — https://dashboard.vapi.ai/api-keys
3. **Vapi phone number** — https://dashboard.vapi.ai/phone-numbers (~$2/month)
4. **Node.js** — for localtunnel

> **Note:** New Vapi accounts get $10 free credit — enough to test everything without spending anything!

## Features

| Feature | Description |
|---------|-------------|
| **Opus 4.5** | Best-in-class reasoning for technical discussions |
| **Project context** | Git status, recent files, todos loaded automatically |
| **Live tools** | Claude reads files and searches code during calls |
| **Auto-transcripts** | Every call saved as markdown |
| **Personalized** | Claude greets you by name |
| **Inbound calls** | Call your number and Claude answers |

## Commands

```bash
claude-code-voice setup              # Configure API key, phone, name
claude-code-voice register           # Register current project
claude-code-voice start              # Start server + tunnel (recommended)
claude-code-voice call [topic]       # Have Claude call you
claude-code-voice status             # Check configuration
claude-code-voice config name <name> # Update your name
claude-code-voice config show        # Show all config
claude-code-voice history            # View past calls
```

## Customization

Change voice, model, or language:

```bash
# Voice (provider:voiceId)
claude-code-voice config voice openai:nova          # OpenAI Nova
claude-code-voice config voice elevenlabs:rachel    # ElevenLabs Rachel
claude-code-voice config voice deepgram:asteria     # Deepgram Asteria

# Model
claude-code-voice config model claude-sonnet-4-20250514   # Use Sonnet 4

# Language
claude-code-voice config language es    # Spanish
claude-code-voice config language fr    # French
```

**Supported voice providers:** openai, elevenlabs, deepgram, playht, azure

## How It Works

```
You ──call──▶ Vapi Phone ──webhook──▶ Your Server ──context──▶ Claude Opus 4.5
                                            │
                                      reads your code
```

1. **Setup** stores your Vapi credentials and creates tools
2. **Register** snapshots project context (git, files, todos)
3. **Start** runs server + tunnel, auto-configures Vapi
4. **Call** — Claude has full context about your project

## The `start` Command

The `start` command is the easiest way to get everything running:

```bash
claude-code-voice start
```

It automatically:
- Kills any existing server on port 8765
- Starts the context server
- Starts localtunnel and waits for URL
- Updates all Vapi tools with the new URL
- Configures inbound call webhooks
- Shows your Vapi number for inbound calls

Just keep that terminal open and you're ready for calls.

## Transcripts

Transcripts auto-save to `~/.claude/skills/call/data/transcripts/` when calls end.

Each transcript includes:
- Full conversation
- AI-generated summary
- Call metadata (duration, project, topic)

## Troubleshooting

### "Connection issues" or "404 errors"
Run `claude-code-voice start` — it auto-configures everything when the tunnel URL changes.

### "I don't recognize this number"
Call from the phone number you used during setup.

### Claude can't read files during call
Make sure `claude-code-voice start` is running in a terminal.

### Check your configuration
```bash
claude-code-voice status
```

## As a Claude Code Skill

For `/call` directly in Claude Code:

```bash
git clone https://github.com/abracadabra50/claude-code-voice-skill.git
ln -s /path/to/claude-code-voice-skill ~/.claude/skills/call
```

Then use `/call` in conversations.

## Manual Setup (Advanced)

If you prefer manual control over the server and tunnel:

```bash
# Terminal 1: Start server
claude-code-voice server

# Terminal 2: Start tunnel
npx localtunnel --port 8765

# Terminal 3: Configure (run after each tunnel restart)
claude-code-voice config server-url https://xxx.loca.lt
claude-code-voice configure-inbound
```

## License

MIT
