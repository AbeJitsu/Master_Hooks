# Claude Code Hooks

Hooks are commands that run automatically when Claude performs specific actions. Instead of reminding Claude to do something every time, hooks make it automatic.

## Quick Example

This hook logs every command Claude runs:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.command' >> ~/claude-commands.log"
      }]
    }]
  }
}
```

Add this to `.claude/settings.json` and every bash command gets logged automatically.

## Hook Events

| Event | When It Runs | Can Block? | Common Use |
|-------|--------------|------------|------------|
| **PreToolUse** | Before Claude uses a tool | ✅ Yes | Validate commands, protect files |
| **PostToolUse** | After tool completes | ❌ No | Format code, log changes |
| **UserPromptSubmit** | When you hit Enter | ✅ Yes | Add context, validate input |
| **Stop** | When Claude finishes | ✅ Yes | Enforce todos, run tests |
| **SubagentStop** | When subagent finishes | ✅ Yes | Validate subagent output |
| **Notification** | When Claude alerts you | ❌ No | Custom notifications |
| **PreCompact** | Before context cleanup | ❌ No | Preserve planning state |
| **SessionStart** | When session begins | ❌ No | Load context, show todos |
| **SessionEnd** | When session ends | ❌ No | Archive session, cleanup |

**Blocking hooks** can stop operations and provide feedback to Claude.

## Your First Hook (5 Minutes)

### 1. Install jq

```bash
# macOS
brew install jq

# Linux
sudo apt install jq
```

### 2. Add hook configuration

Type `/hooks` in Claude Code, or edit `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.command' >> ~/.claude/bash-log.txt"
      }]
    }]
  }
}
```

### 3. Save and test

- Save as "User settings" (applies everywhere)
- Ask Claude to run: `ls`
- Check your log: `cat ~/.claude/bash-log.txt`

You should see the command logged!

## Hook Configuration

### Basic Structure

```json
{
  "hooks": {
    "EventName": [{
      "matcher": "ToolPattern",  // Optional for some events
      "hooks": [{
        "type": "command",
        "command": "your-command-here"
      }]
    }]
  }
}
```

### Matchers (PreToolUse and PostToolUse only)

```json
"Bash"           // Only bash commands
"Edit|Write"     // Edit OR Write tools
"*"              // All tools (or use "" or omit matcher)
```

### Exit Codes (How hooks respond)

| Code | Meaning | What Happens |
|------|---------|--------------|
| **0** | Success | Continue (stdout shown in transcript) |
| **2** | Block | Stop operation, show stderr to Claude |
| **Other** | Warning | Continue, show stderr to user |

### Using Project Scripts

```json
{
  "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/my_hook.py"
}
```

`$CLAUDE_PROJECT_DIR` always points to your project root.

## Common Patterns

### Protect Files

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "if echo \"$FILE\" | grep -q '.env'; then echo 'Cannot edit .env!' >&2; exit 2; fi"
      }]
    }]
  }
}
```

### Auto-Format Code

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "if [[ \"$FILE\" =~ \\.js$ ]]; then prettier --write \"$FILE\"; fi"
      }]
    }]
  }
}
```

### Enforce Todos Before Stopping

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/stop_validator.py"
      }]
    }]
  }
}
```

See `.claude/hooks/stop_validator.py` in this project for a working example.

## Working Examples

This project includes a complete hooks system. Check these files:

- **bash_validator.py** - Blocks dangerous commands
- **stop_validator.py** - Enforces todo completion
- **todo_sync.py** - Syncs TodoWrite with todo.md
- **prompt_enhancer.py** - Adds todo context to prompts
- **pre_compact.py** - Preserves state before compaction
- **session_end.py** - Archives sessions
- **hook_utils.py** - Shared utilities (DRY pattern)

All follow the same pattern:
1. Read JSON from stdin
2. Process/validate
3. Exit with appropriate code
4. Log to activity.log

## Security Warning

⚠️ **Hooks run automatically with your permissions**

- Never copy hooks you don't understand
- Test commands manually first
- Quote file paths: `"$FILE"` not `$FILE`
- Don't put secrets in hook commands
- Hooks timeout after 60 seconds

## What's Next

- **Complete reference**: See [REFERENCE.md](./REFERENCE.md) for full technical specs
- **Examples**: Browse `.claude/hooks/` directory for working code
- **Debug**: Run `claude --debug` to see hook execution details
- **Config**: Run `/hooks` command to manage hooks interactively

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Hook not running | Check `/hooks` - is it registered? |
| Wrong tool name | Matchers are case-sensitive (`Bash` not `bash`) |
| Script not found | Use full paths or `$CLAUDE_PROJECT_DIR` |
| Permission denied | Run `chmod +x script.sh` |
| Hook too slow | 60-second timeout - optimize or split work |

For detailed debugging, see [REFERENCE.md](./REFERENCE.md).
