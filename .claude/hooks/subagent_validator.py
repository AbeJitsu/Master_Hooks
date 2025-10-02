#!/usr/bin/env python3
"""
SubagentStop Hook: Validates subagent task completion and quality.
Provides QA feedback to ensure subagents actually complete their assigned work.
Refactored to use shared utilities following DRY principles.
"""
import sys
import json
from hook_utils import (
    read_hook_input,
    log_activity,
    exit_allow,
    exit_block,
    load_config
)

def read_transcript(transcript_path: str) -> list:
    """
    Read the transcript JSONL file.

    Args:
        transcript_path: Path to transcript file

    Returns:
        List of transcript entries (dicts)
    """
    entries = []
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    except Exception as e:
        log_activity(f"Error reading transcript: {e}", "ERROR")
    return entries

def find_last_subagent_task(entries: list) -> dict:
    """
    Find the most recent Task tool call in transcript.

    Args:
        entries: List of transcript entries

    Returns:
        Dict with task info: {prompt, description, type}
    """
    # Walk backwards through transcript to find last Task call
    for entry in reversed(entries):
        if entry.get('role') == 'assistant':
            content = entry.get('content', [])
            for block in content:
                if block.get('type') == 'tool_use' and block.get('name') == 'Task':
                    tool_input = block.get('input', {})
                    return {
                        'prompt': tool_input.get('prompt', ''),
                        'description': tool_input.get('description', ''),
                        'subagent_type': tool_input.get('subagent_type', 'unknown')
                    }
    return None

def find_subagent_output(entries: list) -> str:
    """
    Find the subagent's final output/report.

    Args:
        entries: List of transcript entries

    Returns:
        The subagent's output text
    """
    # The last user message before SubagentStop is typically the subagent's report
    for entry in reversed(entries):
        if entry.get('role') == 'user':
            content = entry.get('content', [])
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    return block.get('text', '')
                elif isinstance(block, str):
                    return block
    return ""

def analyze_subagent_quality(task_info: dict, output: str, config: dict) -> tuple:
    """
    Analyze if subagent completed task successfully.

    Args:
        task_info: Dict with task prompt/description
        output: Subagent's output text
        config: Hook configuration

    Returns:
        Tuple of (is_valid, feedback_message)
    """
    if not task_info:
        return True, "No task info found - allowing"

    qa_config = config.get('subagent_validator', {})
    min_output_length = qa_config.get('min_output_length', 50)
    error_keywords = qa_config.get('error_keywords', [
        'error', 'failed', 'could not', 'unable to', 'not found'
    ])

    # Check 1: Minimum output length
    if len(output.strip()) < min_output_length:
        return False, f"Subagent output too short ({len(output)} chars). Task was: {task_info['description']}"

    # Check 2: Look for error indicators
    output_lower = output.lower()
    for keyword in error_keywords:
        if keyword in output_lower and 'success' not in output_lower:
            return False, f"Subagent appears to have failed (found '{keyword}'). Review output and retry if needed."

    # Check 3: Empty or placeholder responses
    if output.strip() in ['', 'None', 'N/A', 'TODO', 'Not implemented']:
        return False, f"Subagent returned placeholder/empty response for: {task_info['description']}"

    # Passed basic quality checks
    return True, "Subagent output validated"

def main():
    """Main hook execution."""
    # Load configuration
    config = load_config()
    qa_config = config.get('subagent_validator', {})
    enabled = qa_config.get('enabled', True)

    # Read input
    input_data = read_hook_input()

    # Check if stop hook is already active to prevent infinite loop
    if input_data.get('stop_hook_active', False):
        log_activity("SubagentStop: stop_hook_active=true, allowing to prevent loop", "INFO")
        exit_allow()

    # If validation disabled, allow
    if not enabled:
        log_activity("SubagentStop validation disabled in config", "INFO")
        exit_allow()

    # Get transcript path
    transcript_path = input_data.get('transcript_path')
    if not transcript_path:
        log_activity("No transcript_path in input, allowing", "WARNING")
        exit_allow()

    # Analyze subagent work
    try:
        entries = read_transcript(transcript_path)
        if not entries:
            log_activity("Empty transcript, allowing", "INFO")
            exit_allow()

        task_info = find_last_subagent_task(entries)
        output = find_subagent_output(entries)

        is_valid, feedback = analyze_subagent_quality(task_info, output, config)

        if is_valid:
            log_activity(f"SubagentStop: QA passed - {feedback}", "INFO")
            if task_info:
                log_activity(f"  Task: {task_info['description']}", "INFO")
            exit_allow()
        else:
            log_activity(f"SubagentStop: QA failed - {feedback}", "BLOCKED")
            exit_block(f"\n⚠️ Subagent QA Check Failed:\n{feedback}\n\nPlease review the subagent's work and address any issues.")

    except Exception as e:
        log_activity(f"Error in subagent validation: {e}", "ERROR")
        # Fail open - don't block on errors
        exit_allow()

if __name__ == "__main__":
    main()
