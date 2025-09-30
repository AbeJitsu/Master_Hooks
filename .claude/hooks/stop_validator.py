#!/usr/bin/env python3
"""
Stop Hook: Validates that all TODOs are completed before allowing Claude to stop.
"""
import json
import sys

def parse_transcript(transcript_path):
    """Parse transcript JSONL file and extract TODO states."""
    todos = []
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    # Look for TodoWrite tool calls
                    if entry.get('type') == 'tool_use' and entry.get('name') == 'TodoWrite':
                        tool_input = entry.get('input', {})
                        if 'todos' in tool_input:
                            todos = tool_input['todos']  # Keep latest state
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return []

    return todos

def check_incomplete_todos(todos):
    """Check for incomplete TODOs."""
    incomplete = [t for t in todos if t.get('status') in ['pending', 'in_progress']]
    return incomplete

# Main execution
try:
    input_data = json.load(sys.stdin)
    transcript_path = input_data.get('transcript_path', '')

    # Check if stop hook is already active to prevent infinite loop
    if input_data.get('stop_hook_active', False):
        sys.exit(0)

    todos = parse_transcript(transcript_path)
    incomplete = check_incomplete_todos(todos)

    if incomplete:
        print(f"\n❌ Cannot stop: You have {len(incomplete)} incomplete task(s):\n", file=sys.stderr)
        for i, todo in enumerate(incomplete, 1):
            status = todo.get('status', 'unknown')
            content = todo.get('content', 'Unknown task')
            print(f"  {i}. [{status.upper()}] {content}", file=sys.stderr)
        print("\nPlease complete all tasks before stopping.", file=sys.stderr)
        sys.exit(2)  # Block stopping

    # All complete or no todos
    sys.exit(0)

except Exception as e:
    print(f"Error in stop validator: {e}", file=sys.stderr)
    sys.exit(0)  # Don't block on errors
