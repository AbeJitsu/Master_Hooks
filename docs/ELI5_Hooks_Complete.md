# Claude Code Hooks: The Complete Simple Guide

> Think of hooks as automatic helpers that watch Claude work and jump in when needed - no reminders required!

## What Are Hooks? 🎣

Imagine Claude Code as a worker in your workshop. Hooks are like automatic rules you set up:
- 🔔 Ring a bell when Claude picks up certain tools
- ✅ Check if materials are safe before Claude uses them
- 🧹 Clean up after Claude finishes a task
- 🛑 Stop Claude if they're about to break something important

**In simple terms:** Hooks are commands that run automatically when Claude does specific things, like editing files or running terminal commands. Instead of hoping Claude remembers to do something, hooks make it automatic!

## Why Use Hooks Instead of Just Asking? 🤔

| Without Hooks | With Hooks |
|---------------|------------|
| "Please format this file after editing" | File formats itself automatically |
| "Don't edit production files" | Production files are automatically protected |
| "Let me know when you're done" | You get notified automatically |
| "Log all the commands you run" | Commands are logged without asking |

**Think of it like:** The difference between leaving sticky notes everywhere vs. having automatic systems that just work.

## Quick Start: Your First Hook in 5 Minutes ⚡

Let's create a simple hook that logs every command Claude runs:

### Prerequisites
You need `jq` installed (it helps read JSON data). Install it first if you don't have it.

### Step 1: Open Hook Settings
Type `/hooks` in Claude Code

### Step 2: Pick When It Runs
Choose `PreToolUse` (this means "before Claude uses tools")

### Step 3: Choose What to Watch
Select `+ Add new matcher` and type `Bash` (to watch terminal commands)

### Step 4: Add Your Helper Command
Select `+ Add new hook` and enter:
```bash
jq -r '"Command: \(.tool_input.command)"' >> ~/claude-commands.log
```

### Step 5: Save It
Choose "User settings" to use it everywhere, then press Esc to exit.

**That's it!** Now check `~/claude-commands.log` after Claude runs commands to see your log.

## Understanding Hook Events (When Hooks Run) 📅

Think of these as different moments when your helpers can jump in:

### 1. **PreToolUse** - "Before Claude Picks Up a Tool"
- **Think of it like:** A security guard checking if Claude can use a tool
- **What it does:** Runs before Claude edits files, runs commands, etc.
- **Special power:** Can stop Claude and say "No, don't do that!"
- **Example:** "Before editing any .env file, stop and warn me"

### 2. **PostToolUse** - "After Claude Puts Down a Tool"
- **Think of it like:** A cleanup crew that comes in after Claude finishes
- **What it does:** Runs after Claude successfully uses a tool
- **Special power:** Can give Claude feedback about what just happened
- **Example:** "After editing a Python file, run the formatter"

### 3. **UserPromptSubmit** - "When You Send Claude a Message"
- **Think of it like:** An assistant who adds notes to your message
- **What it does:** Runs when you hit Enter, before Claude reads your message
- **Special power:** Can add context or block inappropriate requests
- **Example:** "Add the current time to every message"

### 4. **Notification** - "When Claude Needs to Tell You Something"
- **Think of it like:** Customizing your doorbell sound
- **What it does:** Runs when Claude needs your attention or permission
- **Example:** "Play a sound when Claude needs permission"

### 5. **Stop** - "When Claude Finishes Talking"
- **Think of it like:** Someone checking if there's more work after Claude stops
- **What it does:** Runs when Claude completes their response
- **Special power:** Can make Claude continue working
- **Example:** "After Claude responds, check if tests still pass"

### 6. **SubagentStop** - "When Claude's Helper Finishes"
- **Think of it like:** Checking a sub-contractor's work
- **What it does:** Runs when Claude's sub-tasks complete
- **Example:** "Log when background tasks finish"

### 7. **PreCompact** - "Before Claude Cleans Up Memory"
- **Think of it like:** Saving important notes before cleaning your desk
- **What it does:** Runs before Claude compresses the conversation
- **Example:** "Save important context before compacting"

### 8. **SessionStart** - "When You Start Working"
- **Think of it like:** Morning briefing when you arrive at work
- **What it does:** Runs when you start Claude Code
- **Special power:** Can load helpful context automatically
- **Example:** "Load today's GitHub issues when I start"

### 9. **SessionEnd** - "When You Stop Working"
- **Think of it like:** Turning off the lights when leaving
- **What it does:** Runs when you close Claude Code
- **Example:** "Save a summary of what was done today"

## How to Configure Hooks 🔧

Hooks live in settings files (think of them as instruction sheets):

### Where Hooks Are Stored

| Location | File | When to Use |
|----------|------|-------------|
| Personal | `~/.claude/settings.json` | Hooks you want everywhere |
| Project | `.claude/settings.json` | Team-shared hooks |
| Local | `.claude/settings.local.json` | Your personal project hooks |

### Basic Structure (Don't Worry, It's Simple!)

```json
{
  "hooks": {
    "EventName": [{
      "matcher": "WhatToWatch",
      "hooks": [{
        "type": "command",
        "command": "your-command-here"
      }]
    }]
  }
}
```

**Think of it like:** A recipe card that says "When THIS happens, watching for THAT, do THIS command"

### Matchers (What to Watch For)

For PreToolUse and PostToolUse, you can watch specific tools:
- `"Bash"` - Only terminal commands
- `"Edit"` - Only file edits
- `"Write"` - Only new files
- `"Edit|Write"` - Either editing OR writing files
- `"*"` - Everything Claude does

## How Hooks Talk to Claude 💬

### What Claude Tells Your Hook
When your hook runs, Claude sends it information (as JSON):
- What tool is being used
- What file is being edited
- What command is being run
- The current folder location

**Think of it like:** Claude filling out a form before your hook runs

### What Your Hook Can Say Back

Your hook responds with an "exit code" - like a traffic light:

| Exit Code | Meaning | What Happens |
|-----------|---------|--------------|
| 0 | 🟢 Green light | "All good, continue!" |
| 2 | 🔴 Red light | "Stop! There's a problem!" (Claude sees the error) |
| Other | 🟡 Yellow light | "Warning, but continue" (You see the warning) |

**Special for exit code 2:**
- PreToolUse: Blocks the tool from running
- PostToolUse: Tells Claude something went wrong
- UserPromptSubmit: Blocks your message
- Stop: Makes Claude continue working

## Common Examples 🌟

### Example 1: Auto-Format Your Code
**What:** Automatically make your code pretty after Claude edits it

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "if [[ $FILE =~ \\.js$ ]]; then prettier --write \"$FILE\"; fi"
      }]
    }]
  }
}
```

### Example 2: Protect Important Files
**What:** Stop Claude from editing your passwords file

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "if [[ $FILE == '.env' ]]; then echo 'Cannot edit .env!' >&2; exit 2; fi"
      }]
    }]
  }
}
```

### Example 3: Desktop Notifications
**What:** Get a popup when Claude needs you

```json
{
  "hooks": {
    "Notification": [{
      "hooks": [{
        "type": "command",
        "command": "notify-send 'Claude needs your attention!'"
      }]
    }]
  }
}
```

### Example 4: Log Everything
**What:** Keep track of all commands Claude runs

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "echo \"$(date): Claude ran a command\" >> ~/claude.log"
      }]
    }]
  }
}
```

## Safety Rules (Important!) 🔒

### The Golden Rules

1. **Hooks run automatically** - They don't ask permission each time
2. **Hooks use YOUR permissions** - They can access anything you can
3. **Check before copying** - Never use hook commands you don't understand
4. **Test first** - Try commands manually before making them hooks
5. **60-second limit** - Hooks timeout after 1 minute

### Think of it Like...
Giving someone your house keys - they can open any door you can. Only give "keys" (hooks) you trust!

### Safe Practices

✅ **DO:**
- Use `"$CLAUDE_PROJECT_DIR"` for project paths
- Quote file paths with spaces: `"$FILE"`
- Test commands manually first
- Start with simple logging hooks
- Document what your hooks do

❌ **DON'T:**
- Put passwords in hook commands
- Copy-paste hooks you don't understand
- Edit system files without protection
- Use commands that wait for input
- Trust hooks from unknown sources

## Troubleshooting Basics 🔧

### "My hook isn't running"
1. **Check it's registered:** Type `/hooks`
2. **Check the matcher:** It's case-sensitive (`Bash` not `bash`)
3. **Make scripts executable:** `chmod +x your-script.sh`
4. **Use debug mode:** Run `claude --debug` to see details

### "My hook runs but doesn't work"
1. **Test manually:** Run the command yourself first
2. **Check permissions:** Make sure files are accessible
3. **Use full paths:** `/usr/bin/python3` not just `python3`
4. **Add logging:** Echo messages to a log file to debug

### "Claude seems stuck"
- Your hook might be taking too long (60-second limit)
- Check if your hook is waiting for input (it shouldn't)
- Use `claude --debug` to see what's happening

### Common Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Quotes not escaped in JSON | Use `\"` inside JSON strings |
| Wrong tool names | Check exact names (case matters!) |
| Relative paths | Use absolute paths or `$CLAUDE_PROJECT_DIR` |
| Commands need input | Hooks can't interact - make them automatic |

## Advanced Features (When You're Ready) 🚀

### JSON Output for More Control
Instead of just exit codes, hooks can return JSON for fine control:

```json
{
  "permissionDecision": "deny",
  "permissionDecisionReason": "This file is protected"
}
```

### Working with MCP Tools
MCP tools have special names like `mcp__github__search`. You can hook them too:

```json
{
  "matcher": "mcp__.*",
  "hooks": [...]
}
```

### Multiple Hooks
You can have many hooks for the same event - they all run in parallel!

## Getting Help 🆘

- **See your hooks:** Type `/hooks`
- **General help:** Type `/help`
- **Debug mode:** Run `claude --debug`
- **Check logs:** Look at your hook output files
- **Start simple:** Begin with echo commands

## Summary Cheat Sheet 📝

| Event | When It Runs | Can Block? | Common Use |
|-------|--------------|------------|------------|
| PreToolUse | Before tools | Yes ✅ | Validate/protect |
| PostToolUse | After tools | No ❌ | Format/cleanup |
| UserPromptSubmit | You hit Enter | Yes ✅ | Add context |
| Notification | Claude alerts | No ❌ | Custom alerts |
| Stop | Claude finishes | Yes ✅ | Continue work |
| SessionStart | You start | No ❌ | Load context |
| SessionEnd | You exit | No ❌ | Save/cleanup |

---

**Remember:** Hooks are like training wheels for Claude - they ensure certain things always happen the right way, every time. Start with one simple hook, see how it works, then gradually add more as you get comfortable. You've got this! 🎯