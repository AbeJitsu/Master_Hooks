#!/usr/bin/env python3
"""
Prompt Enhancer Hook: Adds todo context to user prompts.
Ensures Claude is always aware of current tasks without manual reminders.
Refactored to use shared utilities following DRY principles.
"""
import sys
from hook_utils import (
    read_hook_input,
    format_todo_for_claude,
    log_activity,
    exit_allow
)

def main():
    """Main hook execution."""
    # Read input
    input_data = read_hook_input()

    # Get current prompt
    prompt = input_data.get('prompt', '')
    if not prompt:
        exit_allow()

    # Don't enhance if user is already asking about todos
    todo_keywords = ['todo', 'task', 'checklist', 'incomplete', 'completed']
    if any(keyword in prompt.lower() for keyword in todo_keywords):
        exit_allow()  # Let original prompt pass through

    # Get todo context
    todo_context = format_todo_for_claude()

    # Only enhance if we have meaningful context
    if todo_context and 'No todo.md file found' not in todo_context:
        if 'pending' in todo_context.lower() or 'completed' in todo_context.lower():
            # Output context to stderr (will be added to prompt)
            print(f"\n{todo_context}", file=sys.stderr)
            log_activity("Prompt enhanced with todo context", "INFO")

    exit_allow()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Prompt enhancer error: {e}", file=sys.stderr)
        exit_allow()  # Don't block on errors