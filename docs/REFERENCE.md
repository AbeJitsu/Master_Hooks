# Hooks Reference

Complete technical specification for Claude Code hooks.

## Hook Events

### PreToolUse

Runs before Claude executes a tool. Can block the operation.

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la",
    "description": "List files"
  }
}
```

**Output (Exit Code 2):** Blocks tool, stderr shown to Claude
**Common matchers:** `Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `Task`

**Example:**
```python
#!/usr/bin/env python3
import json, sys, re

input_data = json.load(sys.stdin)
command = input_data.get('tool_input', {}).get('command', '')

if re.search(r'rm\s+-rf\s+/', command):
    print("❌ Dangerous command blocked!", file=sys.stderr)
    sys.exit(2)  # Block

sys.exit(0)  # Allow
```

---

### PostToolUse

Runs after a tool completes successfully.

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.ts",
    "content": "..."
  },
  "tool_response": {
    "filePath": "/path/to/file.ts",
    "success": true
  }
}
```

**Output (Exit Code 2):** Provides feedback to Claude (tool already ran)
**Common use:** Formatting, linting, logging

**Example:**
```bash
# Auto-format TypeScript files
jq -r '.tool_input.file_path' | {
  read file;
  if [[ "$file" =~ \.ts$ ]]; then
    prettier --write "$file"
  fi
}
```

---

### UserPromptSubmit

Runs when user submits a prompt, before Claude processes it.

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "Help me write a function"
}
```

**Output:**
- Exit 0: stdout added to context for Claude
- Exit 2: Blocks prompt, erases it, stderr shown to user

**Example:**
```python
#!/usr/bin/env python3
import json, sys, datetime

input_data = json.load(sys.stdin)

# Add current time to context
print(f"Current time: {datetime.datetime.now()}", file=sys.stdout)
sys.exit(0)
```

---

### Stop

Runs when Claude finishes responding.

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "hook_event_name": "Stop",
  "stop_hook_active": false
}
```

**Output (Exit Code 2):** Blocks stopping, stderr shown to Claude (forces continuation)
**Common use:** Enforce todo completion, run tests

**Example:**
```python
#!/usr/bin/env python3
import sys

# Check if todos exist
with open('todo.md', 'r') as f:
    if '- [ ]' in f.read():
        print("Complete todos before stopping!", file=sys.stderr)
        sys.exit(2)  # Block stop

sys.exit(0)  # Allow stop
```

---

### SubagentStop

Runs when a subagent (Task tool call) finishes.

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "hook_event_name": "SubagentStop",
  "stop_hook_active": false
}
```

**Output (Exit Code 2):** Blocks subagent from stopping, provides feedback

**Example:** Validate subagent output meets quality standards.

---

### PreCompact

Runs before Claude compacts conversation history (manual `/compact` or automatic when context full).

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "hook_event_name": "PreCompact",
  "trigger": "manual",  // or "auto"
  "custom_instructions": ""
}
```

**Output:** Cannot block compaction (non-blocking hook)
**Common use:** Preserve planning state, save session insights, extract todos

**Example:**
```python
#!/usr/bin/env python3
import json, sys

input_data = json.load(sys.stdin)
trigger = input_data.get('trigger')

if trigger == 'auto':
    # Extract and save important context before auto-compaction
    # Read transcript, save todos, planning notes to snapshot file
    print("🔄 Context preserved before auto-compaction", file=sys.stderr)

sys.exit(0)
```

See `.claude/hooks/pre_compact.py` for full implementation.

---

### SessionStart

Runs when Claude Code starts a session.

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "hook_event_name": "SessionStart",
  "source": "startup"  // or "resume", "clear", "compact"
}
```

**Output:** stdout added to context for Claude
**Common use:** Load project context, show todo status, display recent changes

**Example:**
```python
#!/usr/bin/env python3
import sys

# Load todos and show status
with open('todo.md', 'r') as f:
    content = f.read()
    incomplete = content.count('- [ ]')
    print(f"📋 Session started: {incomplete} pending tasks", file=sys.stdout)

sys.exit(0)
```

---

### SessionEnd

Runs when session ends.

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "SessionEnd",
  "reason": "clear"  // or "logout", "prompt_input_exit", "other"
}
```

**Output:** Cannot block session end (non-blocking hook)
**Common use:** Archive session, generate summary, cleanup, log rotation

**Example:**
```python
#!/usr/bin/env python3
import json, sys, datetime

input_data = json.load(sys.stdin)
reason = input_data.get('reason')

# Generate session summary
summary_file = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
# ... analyze transcript, create summary ...

print(f"📊 Session ended ({reason}), summary saved", file=sys.stderr)
sys.exit(0)
```

See `.claude/hooks/session_end.py` for full implementation.

---

### Notification

Runs when Claude sends notifications.

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "Notification",
  "message": "Claude needs your permission"
}
```

**Output:** Cannot block
**Common use:** Custom desktop notifications, sounds, alerts

---

## Configuration

### Settings Files (Priority Order)

1. **Enterprise policy** (highest priority)
2. **`~/.claude/settings.json`** - User settings (all projects)
3. **`.claude/settings.json`** - Project settings (team-shared)
4. **`.claude/settings.local.json`** - Local overrides (not committed)

### Complete Structure

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",  // Optional (only for PreToolUse, PostToolUse)
        "hooks": [
          {
            "type": "command",
            "command": "your-command",
            "timeout": 60000  // Optional, milliseconds (default: 60000)
          }
        ]
      }
    ]
  }
}
```

### Matchers (Regex Patterns)

```json
"Bash"              // Exact match
"Edit|Write"        // OR pattern
"Notebook.*"        // Wildcard
"mcp__.*"           // All MCP tools
"mcp__github__.*"   // Specific MCP server
"*"                 // All tools (or use "" or omit)
```

### Environment Variables

- **`$CLAUDE_PROJECT_DIR`** - Absolute path to project root
- **`$FILE`** - File path (some hooks)
- All system environment variables available

---

## Hook Output Formats

### Exit Codes (Simple)

```python
sys.exit(0)  # Allow/success
sys.exit(2)  # Block/error (shown to Claude)
sys.exit(1)  # Warning (shown to user only)
```

### JSON Output (Advanced)

```python
import json

output = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",  # or "allow", "ask"
        "permissionDecisionReason": "File is protected"
    },
    "suppressOutput": True,  # Hide from transcript
    "systemMessage": "Optional warning to user"
}

print(json.dumps(output))
sys.exit(0)
```

**PreToolUse decisions:**
- `"allow"` - Bypass permission system
- `"deny"` - Block tool, show reason to Claude
- `"ask"` - Prompt user for confirmation

**PostToolUse:**
```json
{
  "decision": "block",  // or undefined
  "reason": "Linting failed: 3 errors",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Details for Claude"
  }
}
```

**UserPromptSubmit:**
```json
{
  "decision": "block",  // Block prompt
  "reason": "Sensitive content detected",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Additional context if not blocked"
  }
}
```

**Stop/SubagentStop:**
```json
{
  "decision": "block",  // Force continue
  "reason": "Must complete: 3 tasks remaining"
}
```

---

## Examples by Use Case

### Validation

**Bash Command Validator:**
```python
#!/usr/bin/env python3
import json, sys, re

DANGEROUS = [
    r'rm\s+-rf\s+/',
    r'dd\s+.*of=/dev/',
    r'chmod\s+-R\s+777'
]

input_data = json.load(sys.stdin)
cmd = input_data.get('tool_input', {}).get('command', '')

for pattern in DANGEROUS:
    if re.search(pattern, cmd):
        print(f"❌ Blocked dangerous pattern: {pattern}", file=sys.stderr)
        sys.exit(2)

sys.exit(0)
```

**File Protection:**
```python
#!/usr/bin/env python3
import json, sys

PROTECTED = ['.env', 'package-lock.json', '.git/']

input_data = json.load(sys.stdin)
file_path = input_data.get('tool_input', {}).get('file_path', '')

if any(p in file_path for p in PROTECTED):
    print(f"❌ Cannot modify protected file: {file_path}", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
```

---

### Automation

**Auto-Format JavaScript:**
```bash
#!/bin/bash
jq -r '.tool_input.file_path' | {
  read file
  if [[ "$file" =~ \.(js|ts)$ ]]; then
    prettier --write "$file" 2>&1 | grep -v "^$"
  fi
}
```

**Todo Sync (PostToolUse on TodoWrite):**
```python
#!/usr/bin/env python3
import json, sys

input_data = json.load(sys.stdin)
todos = input_data.get('tool_input', {}).get('todos', [])

# Write to todo.md
with open('todo.md', 'w') as f:
    f.write("# Todo List\n\n")
    for todo in todos:
        status = 'x' if todo['status'] == 'completed' else ' '
        f.write(f"- [{status}] {todo['content']}\n")

print("✅ Todos synced", file=sys.stderr)
sys.exit(0)
```

---

### State Management

**PreCompact - State Preservation:**
```python
#!/usr/bin/env python3
import json, sys, datetime

input_data = json.load(sys.stdin)
trigger = input_data.get('trigger')
transcript = input_data.get('transcript_path')

# Extract latest todos from transcript
todos = extract_todos_from_transcript(transcript)

# Save snapshot
snapshot = {
    'timestamp': datetime.datetime.now().isoformat(),
    'trigger': trigger,
    'todos': todos,
    'planning_insights': extract_planning_notes(transcript)
}

with open('.claude/state/pre_compact_snapshot.json', 'w') as f:
    json.dump(snapshot, f, indent=2)

print(f"🔄 State preserved ({len(todos)} tasks)", file=sys.stderr)
sys.exit(0)
```

**SessionEnd - Session Archive:**
```python
#!/usr/bin/env python3
import json, sys, datetime

input_data = json.load(sys.stdin)
reason = input_data.get('reason')
transcript = input_data.get('transcript_path')

# Generate summary
summary = analyze_transcript(transcript)

# Save archive
date_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
archive_file = f".claude/sessions/session_{date_str}.md"

with open(archive_file, 'w') as f:
    f.write(summary)

print(f"📊 Session ended ({reason}), summary saved", file=sys.stderr)
sys.exit(0)
```

---

### Context Enhancement

**Prompt Enhancer - Add Todo Context:**
```python
#!/usr/bin/env python3
import sys

# Skip if user is asking about todos
input_data = json.load(sys.stdin)
prompt = input_data.get('prompt', '').lower()

if 'todo' in prompt or 'task' in prompt:
    sys.exit(0)  # User already asking about todos

# Add todo context
with open('todo.md', 'r') as f:
    incomplete = [line for line in f if '- [ ]' in line]

if incomplete:
    print(f"\n📋 Current tasks ({len(incomplete)} incomplete):", file=sys.stdout)
    for task in incomplete[:5]:
        print(f"  {task.strip()}", file=sys.stdout)

sys.exit(0)
```

---

## Security Best Practices

### Input Validation

```python
# Always validate and sanitize
import re

file_path = input_data.get('tool_input', {}).get('file_path', '')

# Block path traversal
if '..' in file_path:
    print("Path traversal detected", file=sys.stderr)
    sys.exit(2)

# Validate against whitelist
if not re.match(r'^[a-zA-Z0-9_/.-]+$', file_path):
    print("Invalid characters in path", file=sys.stderr)
    sys.exit(2)
```

### Safe Shell Commands

```bash
# Always quote variables
command="$CLAUDE_PROJECT_DIR/script.sh"

# Never do this:
command=$CLAUDE_PROJECT_DIR/script.sh  # Vulnerable to spaces
```

### Fail-Open Pattern

```python
#!/usr/bin/env python3
import sys

try:
    # Hook logic here
    pass
except Exception as e:
    # Log error but don't block Claude
    print(f"Hook error: {e}", file=sys.stderr)
    sys.exit(0)  # Allow operation to continue
```

---

## Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Hook not running | Not registered | Check `/hooks` or settings.json |
| Script not found | Wrong path | Use `$CLAUDE_PROJECT_DIR` or absolute path |
| Permission denied | Not executable | Run `chmod +x script.sh` |
| Timeout | Too slow (>60s) | Optimize or increase timeout |
| Wrong tool name | Case mismatch | Matchers are case-sensitive |
| Syntax error | Invalid JSON | Validate settings.json |

### Debug Mode

```bash
claude --debug
```

Shows:
- Which hooks match
- Commands executed
- Exit codes and output
- Execution time

### Testing Hooks

```bash
# Test manually with mock input
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | \
  python3 .claude/hooks/bash_validator.py

# Check exit code
echo $?
```

### Logging Pattern

```python
#!/usr/bin/env python3
import sys, datetime

def log(message):
    with open('.claude/hooks/activity.log', 'a') as f:
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{ts}] {message}\n")

log("Hook executed successfully")
```

---

## Hook Execution Details

- **Parallelization:** All matching hooks run in parallel
- **Deduplication:** Identical commands run only once
- **Timeout:** 60 seconds default (configurable per hook)
- **Environment:** Inherits Claude Code's environment
- **Working directory:** Set to cwd from hook input
- **Transcript access:** Full session history in jsonl file

### Output Visibility

| Event | Exit 0 stdout | Exit 2 stderr |
|-------|---------------|---------------|
| PreToolUse | User sees in transcript (Ctrl-R) | Claude sees |
| PostToolUse | User sees in transcript | Claude sees |
| UserPromptSubmit | **Claude sees (added to context)** | User sees only |
| Stop | User sees in transcript | Claude sees |
| SubagentStop | User sees in transcript | Subagent Claude sees |
| Notification | Debug only | Debug only |
| PreCompact | Debug only | User sees |
| SessionStart | **Claude sees (added to context)** | User sees |
| SessionEnd | Debug only | User sees |

---

## MCP Tools Integration

MCP tools use pattern: `mcp__<server>__<tool>`

Examples:
- `mcp__memory__create_entities`
- `mcp__github__search_repositories`
- `mcp__filesystem__read_file`

**Match all MCP tools:**
```json
{
  "matcher": "mcp__.*"
}
```

**Match specific server:**
```json
{
  "matcher": "mcp__github__.*"
}
```

**Match operation type:**
```json
{
  "matcher": "mcp__.*__write.*"
}
```

---

## Working Examples

This project includes complete implementations:

- **`.claude/hooks/bash_validator.py`** - Command validation with dangerous patterns
- **`.claude/hooks/stop_validator.py`** - Enforce todo completion
- **`.claude/hooks/todo_sync.py`** - Sync TodoWrite to todo.md
- **`.claude/hooks/prompt_enhancer.py`** - Add todo context to prompts
- **`.claude/hooks/pre_compact.py`** - Preserve state before compaction
- **`.claude/hooks/session_end.py`** - Archive sessions with summaries
- **`.claude/hooks/hook_utils.py`** - Shared utilities (DRY pattern)
- **`.claude/hooks/config.json`** - Centralized configuration
- **`.claude/settings.json`** - Hook registration

All follow best practices:
- Fail-open error handling
- Centralized configuration
- Comprehensive logging
- Input validation
- Clear exit codes

Study these for production-ready patterns.
