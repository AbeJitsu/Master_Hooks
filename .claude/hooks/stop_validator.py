#!/usr/bin/env python3
"""
Stop Hook: Validates that all TODOs are completed before allowing Claude to stop.
Checks todo.md file for incomplete tasks.
Refactored to use shared utilities following DRY principles.
"""
from hook_utils import (
    read_hook_input,
    read_todo_tasks,
    log_activity,
    exit_allow,
    exit_block,
    load_config
)

def main():
    """Main hook execution."""
    # Load configuration
    config = load_config()
    stop_config = config.get('stop_validator', {})
    enforce_todos = stop_config.get('enforce_todos', True)

    # Read input
    input_data = read_hook_input()

    # Check if stop hook is already active to prevent infinite loop
    if input_data.get('stop_hook_active', False):
        exit_allow()

    # If not enforcing todos, allow stop
    if not enforce_todos:
        exit_allow()

    # Check for incomplete todos
    incomplete, completed = read_todo_tasks()

    if incomplete:
        log_activity(f"Stop blocked: {len(incomplete)} incomplete tasks", "BLOCKED")
        message = f"\n❌ Cannot stop: You have {len(incomplete)} incomplete task(s):\n\n"
        for i, task in enumerate(incomplete, 1):
            message += f"  {i}. {task}\n"
        message += "\nPlease complete all tasks in todo.md before stopping."
        exit_block(message)

    # All complete or no todos
    log_activity("Stop allowed: All tasks complete", "INFO")
    exit_allow()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error in stop validator: {e}", file=sys.stderr)
        exit_allow()  # Don't block on errors