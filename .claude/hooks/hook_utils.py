#!/usr/bin/env python3
"""
Shared utilities for Claude Code hooks.
Consolidates common patterns across all hooks to follow DRY principles.
"""
import json
import sys
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Constants
DEFAULT_PROJECT_DIR = '.'

def get_project_dir() -> str:
    """Get the Claude project directory from environment."""
    return os.environ.get('CLAUDE_PROJECT_DIR', DEFAULT_PROJECT_DIR)

def get_activity_log_path() -> str:
    """Get the path to activity.log file."""
    return os.path.join(get_project_dir(), '.claude', 'hooks', 'activity.log')

def get_todo_file_path() -> str:
    """Get the path to todo.md file."""
    return os.path.join(get_project_dir(), 'todo.md')

def get_config_path() -> str:
    """Get the path to config.json file."""
    return os.path.join(get_project_dir(), '.claude', 'hooks', 'config.json')

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json.
    Returns empty dict if config doesn't exist.
    """
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def read_hook_input() -> Dict[str, Any]:
    """
    Read and parse JSON input from stdin.
    Returns empty dict on error (fail-open pattern).
    """
    try:
        return json.load(sys.stdin)
    except Exception as e:
        print(f"Error reading hook input: {e}", file=sys.stderr)
        return {}

def log_activity(message: str, activity_type: str = "INFO") -> None:
    """
    Log a message to activity.log with timestamp.

    Args:
        message: The message to log
        activity_type: Type of activity (INFO, ERROR, WARNING, BLOCKED, etc.)
    """
    try:
        log_file = get_activity_log_path()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {activity_type}: {message}\n"

        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Warning: Could not write to log: {e}", file=sys.stderr)

def read_todo_tasks() -> Tuple[List[str], List[str]]:
    """
    Read tasks from todo.md file.

    Returns:
        Tuple of (incomplete_tasks, completed_tasks)
    """
    todo_file = get_todo_file_path()

    if not os.path.exists(todo_file):
        return [], []

    incomplete = []
    completed = []

    try:
        with open(todo_file, 'r') as f:
            for line in f:
                line_stripped = line.strip()
                # Check for incomplete tasks
                if line_stripped.startswith('- [ ]'):
                    task = line_stripped[6:].strip()
                    if task:  # Only add non-empty tasks
                        incomplete.append(task)
                # Check for completed tasks
                elif line_stripped.startswith('- [x]') or line_stripped.startswith('- [X]'):
                    task = line_stripped[6:].strip()
                    # Remove any trailing checkmarks or emojis
                    task = re.sub(r'\s*[✅✓]$', '', task)
                    if task:  # Only add non-empty tasks
                        completed.append(task)
    except Exception as e:
        print(f"Error reading todo file: {e}", file=sys.stderr)
        return [], []

    return incomplete, completed

def write_todo_file(incomplete_tasks: List[str], completed_tasks: List[str]) -> bool:
    """
    Write tasks to todo.md file.

    Args:
        incomplete_tasks: List of incomplete task descriptions
        completed_tasks: List of completed task descriptions

    Returns:
        True if successful, False otherwise
    """
    todo_file = get_todo_file_path()

    try:
        with open(todo_file, 'w') as f:
            f.write("# Todo List\n\n")

            if incomplete_tasks:
                f.write("## Incomplete Tasks\n")
                for task in incomplete_tasks:
                    f.write(f"- [ ] {task}\n")
                f.write("\n")

            if completed_tasks:
                f.write("## Completed Tasks\n")
                for task in completed_tasks:
                    f.write(f"- [x] {task}\n")
                f.write("\n")

        return True
    except Exception as e:
        print(f"Error writing todo file: {e}", file=sys.stderr)
        return False

def get_todo_summary() -> Dict[str, Any]:
    """
    Get a summary of todo tasks.

    Returns:
        Dictionary with task counts and summary information
    """
    incomplete, completed = read_todo_tasks()
    total = len(incomplete) + len(completed)

    if total == 0:
        return {
            'exists': os.path.exists(get_todo_file_path()),
            'incomplete_tasks': [],
            'completed_tasks': [],
            'total_tasks': 0,
            'progress_percentage': 0,
            'summary': 'No tasks found in todo.md'
        }

    progress_pct = (len(completed) / total) * 100 if total > 0 else 0

    return {
        'exists': True,
        'incomplete_tasks': incomplete,
        'completed_tasks': completed,
        'total_tasks': total,
        'progress_percentage': progress_pct,
        'summary': f"Tasks: {len(incomplete)} pending, {len(completed)} completed ({progress_pct:.0f}% done)"
    }

def format_todo_for_claude(max_incomplete: int = 5, max_completed: int = 3) -> str:
    """
    Format todo data for Claude to understand context.

    Args:
        max_incomplete: Maximum number of incomplete tasks to show
        max_completed: Maximum number of completed tasks to show

    Returns:
        Formatted string for Claude context
    """
    todo_data = get_todo_summary()

    if not todo_data['exists']:
        return "No todo.md file found in project."

    output = [f"\n📋 {todo_data['summary']}"]

    if todo_data['incomplete_tasks']:
        output.append("\n🔴 Pending tasks:")
        for i, task in enumerate(todo_data['incomplete_tasks'][:max_incomplete], 1):
            output.append(f"  {i}. {task}")
        if len(todo_data['incomplete_tasks']) > max_incomplete:
            output.append(f"  ... and {len(todo_data['incomplete_tasks']) - max_incomplete} more")

    if todo_data['completed_tasks'] and len(todo_data['completed_tasks']) <= max_completed:
        output.append("\n✅ Recently completed:")
        for task in todo_data['completed_tasks'][-max_completed:]:
            output.append(f"  • {task}")

    return '\n'.join(output)

def exit_allow(message: Optional[str] = None) -> None:
    """
    Exit with code 0 (allow operation).

    Args:
        message: Optional message to print before exiting
    """
    if message:
        print(message, file=sys.stderr)
    sys.exit(0)

def exit_block(message: Optional[str] = None) -> None:
    """
    Exit with code 2 (block operation).

    Args:
        message: Optional message to print before exiting
    """
    if message:
        print(message, file=sys.stderr)
    sys.exit(2)

def check_pattern_match(text: str, patterns: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Check if text matches any of the given regex patterns.

    Args:
        text: Text to check
        patterns: List of regex patterns

    Returns:
        Tuple of (matches, matching_pattern)
    """
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, pattern
    return False, None