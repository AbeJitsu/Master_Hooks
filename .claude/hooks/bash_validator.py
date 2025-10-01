#!/usr/bin/env python3
"""
PreToolUse Hook for Bash: Validates and logs bash commands before execution.
Blocks dangerous commands and provides transparency into Claude's command execution.
Refactored to use shared utilities following DRY principles.
"""
import sys
from hook_utils import (
    read_hook_input,
    log_activity,
    check_pattern_match,
    exit_allow,
    exit_block,
    load_config
)

# Default patterns (can be overridden by config.json)
DEFAULT_DANGEROUS_PATTERNS = [
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

DEFAULT_WARNING_PATTERNS = [
    r'sudo\s+',  # Sudo commands
    r'rm\s+-rf',  # Any force deletion
    r'git\s+push\s+--force',  # Force push
    r'git\s+reset\s+--hard',  # Hard reset
    r'>>\s*/etc/',  # Writing to system files
    r'pkill',  # Process killing
    r'killall',  # Kill all processes
]

def main():
    """Main hook execution."""
    # Load configuration
    config = load_config()
    bash_config = config.get('bash_validator', {})

    # Get patterns from config or use defaults
    dangerous_patterns = bash_config.get('dangerous_patterns', DEFAULT_DANGEROUS_PATTERNS)
    warning_patterns = bash_config.get('warning_patterns', DEFAULT_WARNING_PATTERNS)

    # Read input
    input_data = read_hook_input()

    # Extract command
    command = input_data.get('tool_input', {}).get('command', '')
    if not command:
        exit_allow()

    # Check for dangerous commands
    is_dangerous, dangerous_pattern = check_pattern_match(command, dangerous_patterns)
    if is_dangerous:
        log_activity(f"Bash: {command}", "BLOCKED")
        exit_block(f"\n🛑 BLOCKED: This command matches a dangerous pattern.\n"
                  f"   Pattern: {dangerous_pattern}\n"
                  f"   Command: {command}\n"
                  f"\nThis command could potentially harm your system and has been blocked.\n"
                  f"If you're certain this is safe, you can disable this hook temporarily.")

    # Check for warning commands
    needs_warning, warning_pattern = check_pattern_match(command, warning_patterns)
    if needs_warning:
        log_activity(f"Bash: {command}", "WARNING")
        print(f"\n⚠️  WARNING: This command requires caution.", file=sys.stderr)
        print(f"   Pattern: {warning_pattern}", file=sys.stderr)
        print(f"   Command: {command}", file=sys.stderr)
        print("\nProceeding with execution. Please review the command carefully.", file=sys.stderr)
    else:
        log_activity(f"Bash: {command}", "ALLOWED")

    exit_allow()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error in bash validator: {e}", file=sys.stderr)
        exit_allow()  # Fail open