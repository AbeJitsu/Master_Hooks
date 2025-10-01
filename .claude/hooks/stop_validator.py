#!/usr/bin/env python3
"""
Stop Hook: Validates that all TODOs are completed before allowing Claude to stop.
Checks todo.md file for incomplete tasks.
"""
import json
import sys
import os
import re

def check_todo_file():
    """Check todo.md file for incomplete tasks."""
    incomplete_tasks = []

    # Get project directory
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
    todo_file = os.path.join(project_dir, 'todo.md')

    # Check if todo.md exists
    if not os.path.exists(todo_file):
        return []

    try:
        with open(todo_file, 'r') as f:
            for line in f:
                # Look for unchecked checkboxes: - [ ]
                if re.match(r'^- \[ \]', line.strip()):
                    task = line.strip()[6:].strip()  # Remove "- [ ] " prefix
                    incomplete_tasks.append(task)
    except Exception as e:
        print(f"Error reading todo.md: {e}", file=sys.stderr)
        return []

    return incomplete_tasks

# Main execution
try:
    input_data = json.load(sys.stdin)

    # Check if stop hook is already active to prevent infinite loop
    if input_data.get('stop_hook_active', False):
        sys.exit(0)

    # Check for incomplete todos in todo.md
    incomplete = check_todo_file()

    if incomplete:
        print(f"\n❌ Cannot stop: You have {len(incomplete)} incomplete task(s):\n", file=sys.stderr)
        for i, task in enumerate(incomplete, 1):
            print(f"  {i}. {task}", file=sys.stderr)
        print("\nPlease complete all tasks in todo.md before stopping.", file=sys.stderr)
        sys.exit(2)  # Block stopping

    # All complete or no todos
    sys.exit(0)

except Exception as e:
    print(f"Error in stop validator: {e}", file=sys.stderr)
    sys.exit(0)  # Don't block on errors