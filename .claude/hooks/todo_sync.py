#!/usr/bin/env python3
"""
Todo Sync Hook: Syncs Claude's TodoWrite tool with todo.md file.
Ensures both tracking systems stay aligned.
Refactored to use shared utilities following DRY principles.
"""
import sys
from hook_utils import (
    read_hook_input,
    read_todo_tasks,
    write_todo_file,
    log_activity,
    exit_allow,
    load_config
)

def sync_claude_todos(claude_todos):
    """
    Sync Claude's todos with existing todo.md file.

    Args:
        claude_todos: List of todo dicts from Claude's TodoWrite tool

    Returns:
        Tuple of (success, message)
    """
    # Parse Claude's todos
    claude_incomplete = []
    claude_completed = []

    for todo in claude_todos:
        task = todo.get('content', '')
        status = todo.get('status', 'pending')

        if status == 'completed':
            claude_completed.append(task)
        else:  # pending or in_progress
            claude_incomplete.append(task)

    # Get sync mode from config
    config = load_config()
    sync_mode = config.get('todo_sync', {}).get('sync_mode', 'merge')

    if sync_mode == 'replace':
        # Complete replacement - Claude's todos are the source of truth
        file_incomplete = claude_incomplete
        file_completed = claude_completed
    else:
        # Original merge logic for backward compatibility
        # Read existing todos
        file_incomplete, file_completed = read_todo_tasks()

        # Merge todos (Claude's take precedence for conflicts)
        # Add new completed tasks from Claude
        for task in claude_completed:
            if task not in file_completed and task not in file_incomplete:
                file_completed.append(task)
            # Move from incomplete to completed if Claude marked it done
            elif task in file_incomplete:
                file_incomplete.remove(task)
                if task not in file_completed:
                    file_completed.append(task)

        # Add new incomplete tasks from Claude
        for task in claude_incomplete:
            if task not in file_incomplete and task not in file_completed:
                file_incomplete.append(task)

    # Write updated todos
    if write_todo_file(file_incomplete, file_completed):
        mode_msg = f"[{sync_mode} mode]"
        return True, f"{mode_msg} {len(file_incomplete)} pending, {len(file_completed)} done"
    else:
        return False, "Failed to write todo.md"

def main():
    """Main hook execution."""
    # Load configuration
    config = load_config()
    sync_config = config.get('todo_sync', {})
    auto_sync = sync_config.get('auto_sync_enabled', True)

    if not auto_sync:
        exit_allow()

    # Read input
    input_data = read_hook_input()

    # Check if this is a TodoWrite tool use
    tool_name = input_data.get('tool_name', '')
    if tool_name != 'TodoWrite':
        exit_allow()

    # Extract todos from tool input
    tool_input = input_data.get('tool_input', {})
    todos = tool_input.get('todos', [])

    # Always sync, even if todos is empty (to clear the file in replace mode)
    success, message = sync_claude_todos(todos)
    if success:
        log_activity(f"Todo sync: {message}", "INFO")
        print("✅ Todos synced to todo.md", file=sys.stderr)
    else:
        log_activity(f"Todo sync failed: {message}", "ERROR")
        print("⚠️ Todo sync had issues", file=sys.stderr)

    exit_allow()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Todo sync error: {e}", file=sys.stderr)
        exit_allow()  # Don't block on errors