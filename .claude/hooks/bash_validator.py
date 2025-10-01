#!/usr/bin/env python3
"""
PreToolUse Hook for Bash: Validates and logs bash commands before execution.
Blocks dangerous commands and provides transparency into Claude's command execution.
"""
import json
import sys
import os
from datetime import datetime
import re

# Dangerous command patterns to block
DANGEROUS_PATTERNS = [
    r'rm\s+-rf\s+/',  # rm -rf / (root deletion)
    r'rm\s+-rf\s+\*',  # rm -rf * (mass deletion)
    r':\(\)\s*{\s*:\|\s*:&\s*}',  # Fork bomb
    r'>\s*/dev/sd[a-z]',  # Direct disk write
    r'dd\s+.*of=/dev/sd[a-z]',  # dd to disk
    r'chmod\s+-R\s+777\s+/',  # Dangerous permission on root
    r'chown\s+-R.*/',  # Change ownership of root
    r'mkfs\.',  # Format filesystem
    r'curl.*\|\s*sh',  # Curl pipe to shell (common attack vector)
    r'wget.*\|\s*sh',  # Wget pipe to shell
]

# Warning patterns (proceed with caution)
WARNING_PATTERNS = [
    r'sudo\s+',  # Sudo commands
    r'rm\s+-rf',  # Any force deletion
    r'git\s+push\s+--force',  # Force push
    r'git\s+reset\s+--hard',  # Hard reset
    r'>>\s*/etc/',  # Writing to system files
    r'pkill',  # Process killing
    r'killall',  # Kill all processes
]

def log_command(command, status, log_file):
    """Log command to activity file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] Bash ({status}): {command}\n"

    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Warning: Could not write to log: {e}", file=sys.stderr)

def check_dangerous_command(command):
    """Check if command matches dangerous patterns."""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, pattern
    return False, None

def check_warning_command(command):
    """Check if command needs a warning."""
    for pattern in WARNING_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, pattern
    return False, None

def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract command from tool_input
        tool_input = input_data.get('tool_input', {})
        command = tool_input.get('command', '')

        # Get project directory for logging
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
        log_file = os.path.join(project_dir, '.claude', 'hooks', 'activity.log')

        # Check for dangerous commands
        is_dangerous, dangerous_pattern = check_dangerous_command(command)
        if is_dangerous:
            log_command(command, "BLOCKED", log_file)
            print(f"\n🛑 BLOCKED: This command matches a dangerous pattern.", file=sys.stderr)
            print(f"   Pattern: {dangerous_pattern}", file=sys.stderr)
            print(f"   Command: {command}", file=sys.stderr)
            print("\nThis command could potentially harm your system and has been blocked.", file=sys.stderr)
            print("If you're certain this is safe, you can disable this hook temporarily.", file=sys.stderr)
            sys.exit(2)  # Block execution

        # Check for warning commands
        needs_warning, warning_pattern = check_warning_command(command)
        if needs_warning:
            log_command(command, "WARNING", log_file)
            print(f"\n⚠️  WARNING: This command requires caution.", file=sys.stderr)
            print(f"   Pattern: {warning_pattern}", file=sys.stderr)
            print(f"   Command: {command}", file=sys.stderr)
            print("\nProceeding with execution. Please review the command carefully.", file=sys.stderr)
            # Continue execution but with warning
        else:
            log_command(command, "ALLOWED", log_file)

        # Allow command to proceed
        sys.exit(0)

    except Exception as e:
        print(f"Error in bash validator: {e}", file=sys.stderr)
        # On error, allow command to proceed (fail open)
        sys.exit(0)

if __name__ == "__main__":
    main()