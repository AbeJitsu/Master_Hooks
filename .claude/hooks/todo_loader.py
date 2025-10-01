#!/usr/bin/env python3
"""
Todo Loader Hook: Reads todo.md and provides formatted status for Claude.
Used in SessionStart and other hooks to give Claude context about current tasks.
Refactored to use shared utilities following DRY principles.
"""
import json
import sys
from hook_utils import (
    get_todo_summary,
    format_todo_for_claude,
    log_activity
)

def main():
    """Main hook execution."""
    import argparse

    parser = argparse.ArgumentParser(description='Todo loader for Claude hooks')
    parser.add_argument('--format', choices=['json', 'text', 'claude'], default='claude',
                       help='Output format')
    parser.add_argument('--session-start', action='store_true',
                       help='Format for SessionStart hook')

    args, unknown = parser.parse_known_args()

    # Get todo data using shared utility
    todo_data = get_todo_summary()

    if args.session_start:
        # Special formatting for SessionStart hook
        log_activity(f"Session started with {len(todo_data['incomplete_tasks'])} pending tasks", "INFO")
        print(f"[Todo Status] {todo_data['summary']}", file=sys.stderr)
        if todo_data['incomplete_tasks']:
            print(f"Priority task: {todo_data['incomplete_tasks'][0]}", file=sys.stderr)
    elif args.format == 'json':
        print(json.dumps(todo_data, indent=2))
    elif args.format == 'text':
        print(todo_data['summary'])
        if todo_data['incomplete_tasks']:
            print("\nIncomplete:")
            for task in todo_data['incomplete_tasks']:
                print(f"- [ ] {task}")
    else:  # claude format
        print(format_todo_for_claude(), file=sys.stderr)

    sys.exit(0)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error in todo loader: {e}", file=sys.stderr)
        sys.exit(0)  # Fail gracefully