---
name: call
description: Voice conversations with Claude about your projects. Call a phone number to brainstorm, or have Claude call you with updates. (user)
allowed-tools: Bash, Read, Write, AskUserQuestion
user-invocable: true
---

# /call

Voice conversations with Claude about your projects. Call a phone number to brainstorm, or have Claude call you with updates.

## Usage

```
/call                      # Claude calls you about current project
/call "discuss the auth"   # Call with specific topic
/call register             # Register current project for calls
/call sync                 # Pull transcripts from Vapi
/call status               # Show configuration status
```

## Setup

1. Install: `pip install claude-code-voice` or symlink this to `~/.claude/skills/call`
2. Run `claude-code-voice setup` to configure Vapi credentials
3. Register projects with `claude-code-voice register`

## How It Works

When you invoke `/call`, Claude:
1. Gathers project context (git status, todos, recent files)
2. Captures current Claude Code session context
3. Creates a transient Vapi voice assistant with full context
4. Calls your phone number
5. Converses naturally about your project
6. Can read files and search code live during the call

## Context Server (Optional)

For live file reading during calls:

```bash
# Terminal 1
claude-code-voice server

# Terminal 2
npx localtunnel --port 8765
```

## Requirements

- Vapi account with phone number
- Python 3.8+
