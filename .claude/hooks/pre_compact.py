#!/usr/bin/env python3
"""
PreCompact Hook: Preserves critical planning state before context compaction.
Handles both manual (/compact) and automatic (context full) compaction triggers.
"""
import json
import os
from datetime import datetime
from hook_utils import (
    read_hook_input,
    log_activity,
    exit_allow,
    load_config,
    get_project_dir
)

def extract_latest_todos(transcript_path):
    """
    Extract the latest TodoWrite state from the transcript.

    Args:
        transcript_path: Path to the session transcript JSONL file

    Returns:
        List of todo dictionaries or empty list
    """
    if not os.path.exists(transcript_path):
        return []

    latest_todos = []
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    # Look for assistant messages with TodoWrite tool use
                    if entry.get('type') == 'assistant' and 'message' in entry:
                        msg = entry['message']
                        for item in msg.get('content', []):
                            if item.get('type') == 'tool_use' and item.get('name') == 'TodoWrite':
                                tool_input = item.get('input', {})
                                if 'todos' in tool_input:
                                    latest_todos = tool_input['todos']
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        log_activity(f"Error reading transcript: {e}", "ERROR")
        return []

    return latest_todos

def extract_planning_insights(transcript_path, look_back_lines=100):
    """
    Extract recent planning discussions and insights from the transcript.

    Args:
        transcript_path: Path to the session transcript JSONL file
        look_back_lines: How many recent lines to analyze

    Returns:
        List of insight strings
    """
    if not os.path.exists(transcript_path):
        return []

    insights = []
    planning_keywords = ['plan', 'strategy', 'approach', 'design', 'architecture', 'decision']

    try:
        # Read last N lines
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-look_back_lines:] if len(lines) > look_back_lines else lines

        for line in recent_lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)

                # Look for user messages with planning keywords
                if entry.get('type') == 'user' and 'message' in entry:
                    msg = entry['message']
                    for item in msg.get('content', []):
                        if item.get('type') == 'text':
                            text = item.get('text', '').lower()
                            if any(keyword in text for keyword in planning_keywords):
                                insights.append({
                                    'type': 'user_planning',
                                    'text': item.get('text', '')[:200]  # First 200 chars
                                })

                # Look for assistant text responses (not tool calls)
                elif entry.get('type') == 'assistant' and 'message' in entry:
                    msg = entry['message']
                    for item in msg.get('content', []):
                        if item.get('type') == 'text':
                            text = item.get('text', '').lower()
                            if any(keyword in text for keyword in planning_keywords):
                                insights.append({
                                    'type': 'assistant_planning',
                                    'text': item.get('text', '')[:200]
                                })
            except json.JSONDecodeError:
                continue
    except Exception as e:
        log_activity(f"Error extracting insights: {e}", "ERROR")
        return []

    # Return only most recent unique insights (max 10)
    unique_insights = []
    seen_texts = set()
    for insight in reversed(insights):
        text = insight['text'][:100]  # Use first 100 chars for uniqueness check
        if text not in seen_texts:
            unique_insights.append(insight)
            seen_texts.add(text)
        if len(unique_insights) >= 10:
            break

    return list(reversed(unique_insights))

def create_state_snapshot(input_data):
    """
    Create a comprehensive state snapshot before compaction.

    Args:
        input_data: Hook input dictionary

    Returns:
        Snapshot dictionary
    """
    transcript_path = input_data.get('transcript_path', '')
    trigger = input_data.get('trigger', 'unknown')
    session_id = input_data.get('session_id', 'unknown')

    # Extract state
    todos = extract_latest_todos(transcript_path)
    insights = extract_planning_insights(transcript_path)

    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'session_id': session_id,
        'trigger': trigger,
        'todos': {
            'total': len(todos),
            'incomplete': [t for t in todos if t.get('status') in ['pending', 'in_progress']],
            'completed': [t for t in todos if t.get('status') == 'completed']
        },
        'planning_insights': insights,
        'metadata': {
            'transcript_path': transcript_path,
            'compaction_count': 0  # Will be incremented
        }
    }

    return snapshot

def save_snapshot(snapshot, config):
    """
    Save the state snapshot to disk.

    Args:
        snapshot: Snapshot dictionary
        config: Configuration dictionary
    """
    snapshot_path = config.get('pre_compact', {}).get(
        'snapshot_path',
        '.claude/state/pre_compact_snapshot.json'
    )

    full_path = os.path.join(get_project_dir(), snapshot_path)

    try:
        # Load existing snapshot to get compaction count
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                old_snapshot = json.load(f)
                snapshot['metadata']['compaction_count'] = old_snapshot.get('metadata', {}).get('compaction_count', 0) + 1

        # Save new snapshot
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            json.dump(snapshot, f, indent=2)

        return True
    except Exception as e:
        log_activity(f"Failed to save snapshot: {e}", "ERROR")
        return False

def update_insights_file(snapshot, config):
    """
    Update the persistent insights markdown file.

    Args:
        snapshot: Snapshot dictionary
        config: Configuration dictionary
    """
    insights_path = config.get('pre_compact', {}).get(
        'insights_path',
        '.claude/state/session_insights.md'
    )

    full_path = os.path.join(get_project_dir(), insights_path)

    try:
        # Append new insights
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'a') as f:
            f.write(f"\n## Compaction at {snapshot['timestamp']}\n\n")
            f.write(f"**Trigger:** {snapshot['trigger']}\n")
            f.write(f"**Session ID:** {snapshot['session_id']}\n\n")

            if snapshot['todos']['incomplete']:
                f.write("### Active Tasks\n")
                for todo in snapshot['todos']['incomplete']:
                    f.write(f"- [{todo.get('status')}] {todo.get('content')}\n")
                f.write("\n")

            if snapshot['planning_insights']:
                f.write("### Planning Insights\n")
                for insight in snapshot['planning_insights']:
                    f.write(f"- **{insight['type']}:** {insight['text'][:150]}...\n")
                f.write("\n")

            f.write("---\n\n")

        return True
    except Exception as e:
        log_activity(f"Failed to update insights file: {e}", "ERROR")
        return False

def main():
    """Main hook execution."""
    # Load configuration
    config = load_config()
    pre_compact_config = config.get('pre_compact', {})

    if not pre_compact_config.get('enabled', True):
        exit_allow()

    # Read input
    input_data = read_hook_input()

    trigger = input_data.get('trigger', 'unknown')
    session_id = input_data.get('session_id', 'unknown')[:8]  # Short ID

    # Create state snapshot
    snapshot = create_state_snapshot(input_data)

    # Save snapshot
    if save_snapshot(snapshot, config):
        log_activity(f"PreCompact ({trigger}): Saved state snapshot - {len(snapshot['todos']['incomplete'])} active tasks", "INFO")

    # Update insights file if configured
    if pre_compact_config.get('preserve_planning_notes', True):
        update_insights_file(snapshot, config)

    # Output to user
    incomplete_count = len(snapshot['todos']['incomplete'])
    insights_count = len(snapshot['planning_insights'])

    if trigger == 'auto':
        print(f"\n🔄 Auto-compaction triggered - preserving state...", file=sys.stderr)
        print(f"   📝 {incomplete_count} active task(s) preserved", file=sys.stderr)
        if insights_count > 0:
            print(f"   💡 {insights_count} planning insight(s) saved", file=sys.stderr)
    else:
        print(f"\n🔄 Manual compaction - state snapshot created", file=sys.stderr)

    exit_allow()

if __name__ == '__main__':
    import sys
    try:
        main()
    except Exception as e:
        print(f"PreCompact error: {e}", file=sys.stderr)
        exit_allow()  # Fail-open
