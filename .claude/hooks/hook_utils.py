#!/usr/bin/env python3
"""
Shared utilities for Claude Code hooks.

This module consolidates common patterns across all hooks to follow DRY principles.
Provides centralized functions for:
- Hook I/O (reading stdin, exit codes)
- Configuration management (config.json)
- Todo management (reading/writing todo.md)
- Activity logging (centralized audit log)
- Path management (project-aware paths)
- Pattern matching (regex utilities)

Architecture:
    All hooks in this project use these utilities to avoid code duplication.
    The fail-open pattern is used throughout: errors are logged but don't block Claude.

Usage:
    from hook_utils import read_hook_input, log_activity, exit_allow

    input_data = read_hook_input()
    # ... process ...
    log_activity("Hook executed", "INFO")
    exit_allow()

Design Principles:
    1. DRY: Each function exists once, used by all hooks
    2. Fail-open: Errors don't block Claude (graceful degradation)
    3. Centralized config: config.json is single source of truth
    4. Consistent logging: All hooks log to same activity.log
    5. Type hints: All functions have clear signatures
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
    """
    Get the Claude project directory from environment.

    Claude Code sets CLAUDE_PROJECT_DIR to the absolute path of the project root.
    This allows hooks to reference project files regardless of current working directory.

    Returns:
        Absolute path to project directory, or '.' if not set
    """
    return os.environ.get('CLAUDE_PROJECT_DIR', DEFAULT_PROJECT_DIR)

def get_activity_log_path() -> str:
    """
    Get the path to activity.log file.

    Returns:
        Absolute path to .claude/hooks/activity.log
    """
    return os.path.join(get_project_dir(), '.claude', 'hooks', 'activity.log')

def get_todo_file_path() -> str:
    """
    Get the path to todo.md file.

    Returns:
        Absolute path to todo.md in project root
    """
    return os.path.join(get_project_dir(), 'todo.md')

def get_config_path() -> str:
    """
    Get the path to config.json file.

    Returns:
        Absolute path to .claude/hooks/config.json
    """
    return os.path.join(get_project_dir(), '.claude', 'hooks', 'config.json')

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json.

    Provides centralized configuration for all hooks. Each hook reads its settings
    from this config (e.g., config['bash_validator']['dangerous_patterns']).

    Returns:
        Dictionary with hook configurations, or empty dict if config doesn't exist
        or has parse errors (fail-open pattern)

    Example:
        config = load_config()
        patterns = config.get('bash_validator', {}).get('dangerous_patterns', [])
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

    Claude Code sends hook data via stdin as JSON. This function safely reads
    and parses that input. On any error, returns empty dict (fail-open pattern)
    so hooks don't block Claude due to parsing issues.

    Returns:
        Dictionary with hook input data, or empty dict on error

    Hook input structure:
        {
            'session_id': str,
            'transcript_path': str,
            'hook_event_name': str,
            'cwd': str,
            ...event-specific fields...
        }

    Example:
        input_data = read_hook_input()
        command = input_data.get('tool_input', {}).get('command', '')
    """
    try:
        return json.load(sys.stdin)
    except Exception as e:
        print(f"Error reading hook input: {e}", file=sys.stderr)
        return {}

def log_activity(message: str, activity_type: str = "INFO") -> None:
    """
    Log a message to activity.log with timestamp.

    Provides centralized audit logging for all hooks. All hook actions are logged
    here for debugging and compliance. Log file is rotated by SessionEnd hook
    when it exceeds configured size.

    Args:
        message: The message to log
        activity_type: Type of activity (INFO, ERROR, WARNING, BLOCKED, etc.)

    Log format:
        [YYYY-MM-DD HH:MM:SS] TYPE: message

    Example:
        log_activity("Bash command allowed: ls", "INFO")
        log_activity("Dangerous pattern detected", "BLOCKED")
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

    Parses markdown checkbox format:
        - [ ] Incomplete task
        - [x] Completed task

    Returns:
        Tuple of (incomplete_tasks, completed_tasks) as lists of strings

    Example:
        incomplete, completed = read_todo_tasks()
        if incomplete:
            print(f"{len(incomplete)} tasks remaining")
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

    Standard exit for successful hook execution or when operation should proceed.
    For most hooks, exit code 0 means "allow and continue".

    Args:
        message: Optional message to print to stderr before exiting

    Example:
        if command_is_safe:
            exit_allow("Command validated")
    """
    if message:
        print(message, file=sys.stderr)
    sys.exit(0)

def exit_block(message: Optional[str] = None) -> None:
    """
    Exit with code 2 (block operation).

    Blocks the operation and provides feedback to Claude (or user, depending on hook).
    Use this to stop dangerous operations, enforce policies, or provide automated feedback.

    Args:
        message: Optional message to print to stderr (shown to Claude or user)

    Exit code 2 behavior by hook:
        - PreToolUse: Blocks tool, message shown to Claude
        - PostToolUse: Shows message to Claude (tool already ran)
        - UserPromptSubmit: Blocks prompt, message shown to user
        - Stop/SubagentStop: Prevents stopping, message shown to Claude

    Example:
        if is_dangerous_command:
            exit_block("❌ Dangerous command blocked")
    """
    if message:
        print(message, file=sys.stderr)
    sys.exit(2)

def check_pattern_match(text: str, patterns: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Check if text matches any of the given regex patterns.

    Performs case-insensitive regex matching against a list of patterns.
    Returns immediately on first match.

    Args:
        text: Text to check against patterns
        patterns: List of regex pattern strings

    Returns:
        Tuple of (matches: bool, matching_pattern: str or None)

    Example:
        dangerous = ['rm\\s+-rf\\s+/', 'dd\\s+.*of=/dev/']
        matches, pattern = check_pattern_match(command, dangerous)
        if matches:
            exit_block(f"Matched dangerous pattern: {pattern}")
    """
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, pattern
    return False, None