#!/usr/bin/env python3
"""
SessionEnd Hook: Archives session data and generates comprehensive summary.
Handles cleanup, log rotation, and session reporting.
"""
import json
import os
import shutil
from datetime import datetime
from hook_utils import (
    read_hook_input,
    log_activity,
    exit_allow,
    load_config,
    get_project_dir,
    get_activity_log_path
)

def load_pre_compact_snapshot():
    """
    Load pre-compaction snapshot if it exists.

    Returns:
        Snapshot dictionary or None
    """
    snapshot_path = os.path.join(get_project_dir(), '.claude/state/pre_compact_snapshot.json')

    if not os.path.exists(snapshot_path):
        return None

    try:
        with open(snapshot_path, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def analyze_transcript(transcript_path, snapshot=None):
    """
    Analyze the transcript to generate session insights.

    Args:
        transcript_path: Path to session transcript
        snapshot: Pre-compaction snapshot (if available)

    Returns:
        Analysis dictionary
    """
    if not os.path.exists(transcript_path):
        return {
            'total_messages': 0,
            'user_messages': 0,
            'assistant_messages': 0,
            'tool_calls': {},
            'todos': {'incomplete': [], 'completed': []},
            'errors': []
        }

    analysis = {
        'total_messages': 0,
        'user_messages': 0,
        'assistant_messages': 0,
        'tool_calls': {},
        'todos': {'incomplete': [], 'completed': []},
        'errors': [],
        'files_mentioned': set(),
        'compaction_occurred': snapshot is not None
    }

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    entry_type = entry.get('type', '')

                    analysis['total_messages'] += 1

                    if entry_type == 'user':
                        analysis['user_messages'] += 1
                    elif entry_type == 'assistant':
                        analysis['assistant_messages'] += 1

                        # Count tool calls
                        msg = entry.get('message', {})
                        for item in msg.get('content', []):
                            if item.get('type') == 'tool_use':
                                tool_name = item.get('name', 'unknown')
                                analysis['tool_calls'][tool_name] = analysis['tool_calls'].get(tool_name, 0) + 1

                                # Extract latest todos
                                if tool_name == 'TodoWrite':
                                    tool_input = item.get('input', {})
                                    if 'todos' in tool_input:
                                        todos = tool_input['todos']
                                        analysis['todos']['incomplete'] = [t for t in todos if t.get('status') in ['pending', 'in_progress']]
                                        analysis['todos']['completed'] = [t for t in todos if t.get('status') == 'completed']

                                # Extract file mentions
                                if tool_name in ['Write', 'Edit', 'Read']:
                                    tool_input = item.get('input', {})
                                    file_path = tool_input.get('file_path', '')
                                    if file_path:
                                        analysis['files_mentioned'].add(file_path)

                    # Look for error messages
                    elif entry_type == 'tool_result':
                        if entry.get('is_error'):
                            analysis['errors'].append({
                                'tool': entry.get('tool_use_id', 'unknown'),
                                'error': str(entry.get('content', ''))[:200]
                            })

                except json.JSONDecodeError:
                    continue
    except Exception as e:
        log_activity(f"Error analyzing transcript: {e}", "ERROR")

    # If compaction occurred, merge with snapshot data
    if snapshot:
        # Prefer snapshot todos if session todos are empty
        if not analysis['todos']['incomplete'] and snapshot.get('todos', {}).get('incomplete'):
            analysis['todos'] = snapshot['todos']

    analysis['files_mentioned'] = list(analysis['files_mentioned'])
    return analysis

def parse_activity_log():
    """
    Parse activity log to extract file modifications and hook events.

    Returns:
        Dictionary with file changes and hook statistics
    """
    activity_log = get_activity_log_path()

    if not os.path.exists(activity_log):
        return {'file_changes': [], 'hook_events': {}}

    file_changes = []
    hook_events = {}

    try:
        with open(activity_log, 'r') as f:
            for line in f:
                # Extract file changes (Write/Edit logs)
                if 'Write:' in line or 'Edit:' in line:
                    parts = line.split(': ', 2)
                    if len(parts) >= 3:
                        file_changes.append(parts[2].strip())

                # Count hook events
                if 'INFO:' in line or 'BLOCKED:' in line or 'ERROR:' in line:
                    # Extract event type
                    for event_type in ['PreCompact', 'SessionStart', 'Stop', 'Todo sync', 'Bash']:
                        if event_type in line:
                            hook_events[event_type] = hook_events.get(event_type, 0) + 1
    except Exception as e:
        log_activity(f"Error parsing activity log: {e}", "ERROR")

    return {'file_changes': file_changes, 'hook_events': hook_events}

def generate_session_summary(input_data, analysis, activity_data):
    """
    Generate a comprehensive markdown summary of the session.

    Args:
        input_data: Hook input data
        analysis: Transcript analysis
        activity_data: Activity log data

    Returns:
        Markdown string
    """
    session_id = input_data.get('session_id', 'unknown')
    reason = input_data.get('reason', 'unknown')
    cwd = input_data.get('cwd', 'unknown')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    summary = []
    summary.append(f"# Session Summary")
    summary.append(f"\n**Session ID:** `{session_id}`")
    summary.append(f"**Ended:** {timestamp}")
    summary.append(f"**Reason:** {reason}")
    summary.append(f"**Working Directory:** `{cwd}`")
    summary.append(f"\n---\n")

    # Statistics
    summary.append("## Session Statistics\n")
    summary.append(f"- **Total Messages:** {analysis['total_messages']}")
    summary.append(f"- **User Messages:** {analysis['user_messages']}")
    summary.append(f"- **Assistant Messages:** {analysis['assistant_messages']}")

    if analysis.get('compaction_occurred'):
        summary.append(f"- **⚠️ Context Compaction:** Yes (some early conversation history was compressed)")

    summary.append(f"\n### Tool Usage\n")
    if analysis['tool_calls']:
        for tool, count in sorted(analysis['tool_calls'].items(), key=lambda x: -x[1]):
            summary.append(f"- **{tool}:** {count} call(s)")
    else:
        summary.append("- No tools used")

    # Tasks
    summary.append(f"\n## Tasks\n")
    incomplete_count = len(analysis['todos']['incomplete'])
    completed_count = len(analysis['todos']['completed'])

    if incomplete_count > 0:
        summary.append(f"\n### ⚠️ Incomplete Tasks ({incomplete_count})\n")
        for todo in analysis['todos']['incomplete']:
            summary.append(f"- [ ] [{todo.get('status')}] {todo.get('content')}")

    if completed_count > 0:
        summary.append(f"\n### ✅ Completed Tasks ({completed_count})\n")
        for todo in analysis['todos']['completed'][:10]:  # Limit to 10
            summary.append(f"- [x] {todo.get('content')}")
        if completed_count > 10:
            summary.append(f"\n*...and {completed_count - 10} more*")

    if incomplete_count == 0 and completed_count == 0:
        summary.append("- No tasks tracked this session")

    # Files
    summary.append(f"\n## Files Modified\n")
    if activity_data['file_changes']:
        # Deduplicate and show recent
        unique_files = list(dict.fromkeys(activity_data['file_changes']))
        for file_path in unique_files[-20:]:  # Last 20 unique files
            summary.append(f"- `{file_path}`")
        if len(unique_files) > 20:
            summary.append(f"\n*...and {len(unique_files) - 20} more files*")
    else:
        summary.append("- No file modifications logged")

    # Errors
    if analysis['errors']:
        summary.append(f"\n## Errors Encountered ({len(analysis['errors'])})\n")
        for error in analysis['errors'][:5]:  # Show first 5
            summary.append(f"- **Tool:** {error['tool']}")
            summary.append(f"  - {error['error']}\n")

    # Hook Events
    if activity_data['hook_events']:
        summary.append(f"\n## Hook Activity\n")
        for event, count in sorted(activity_data['hook_events'].items(), key=lambda x: -x[1]):
            summary.append(f"- **{event}:** {count} event(s)")

    summary.append(f"\n---\n\n*Generated by SessionEnd hook at {timestamp}*\n")

    return '\n'.join(summary)

def save_session_archive(summary, input_data, config):
    """
    Save session summary to archive directory.

    Args:
        summary: Markdown summary
        input_data: Hook input data
        config: Configuration

    Returns:
        Path to saved file or None
    """
    archive_path = config.get('session_end', {}).get(
        'archive_path',
        '.claude/sessions'
    )

    # Create dated directory structure
    date_str = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H-%M-%S')
    session_dir = os.path.join(get_project_dir(), archive_path, date_str)

    try:
        os.makedirs(session_dir, exist_ok=True)

        session_id = input_data.get('session_id', 'unknown')[:8]
        summary_file = os.path.join(session_dir, f"session_{time_str}_{session_id}.md")

        with open(summary_file, 'w') as f:
            f.write(summary)

        return summary_file
    except Exception as e:
        log_activity(f"Failed to save session archive: {e}", "ERROR")
        return None

def rotate_activity_log(config):
    """
    Rotate activity log if it exceeds configured size.

    Args:
        config: Configuration dictionary
    """
    max_size_mb = config.get('session_end', {}).get('rotate_activity_log_at_mb', 10)
    activity_log = get_activity_log_path()

    if not os.path.exists(activity_log):
        return

    try:
        size_mb = os.path.getsize(activity_log) / (1024 * 1024)

        if size_mb > max_size_mb:
            # Rotate log
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            rotated_log = f"{activity_log}.{timestamp}"
            shutil.move(activity_log, rotated_log)
            log_activity(f"Activity log rotated to {rotated_log}", "INFO")
    except Exception as e:
        log_activity(f"Failed to rotate activity log: {e}", "ERROR")

def cleanup_snapshot():
    """
    Clean up the pre-compaction snapshot after session end.
    """
    snapshot_path = os.path.join(get_project_dir(), '.claude/state/pre_compact_snapshot.json')

    if os.path.exists(snapshot_path):
        try:
            os.remove(snapshot_path)
        except Exception:
            pass  # Silent failure for cleanup

def main():
    """Main hook execution."""
    # Load configuration
    config = load_config()
    session_config = config.get('session_end', {})

    if not session_config.get('enabled', True):
        exit_allow()

    # Read input
    input_data = read_hook_input()

    # Load pre-compaction snapshot (if exists)
    snapshot = load_pre_compact_snapshot()

    # Analyze transcript
    transcript_path = input_data.get('transcript_path', '')
    analysis = analyze_transcript(transcript_path, snapshot)

    # Parse activity log
    activity_data = parse_activity_log()

    # Generate summary
    summary = generate_session_summary(input_data, analysis, activity_data)

    # Save archive
    if session_config.get('generate_summary', True):
        archive_file = save_session_archive(summary, input_data, config)
        if archive_file:
            log_activity(f"Session archived to {archive_file}", "INFO")

    # Cleanup
    if session_config.get('auto_cleanup', True):
        cleanup_snapshot()
        rotate_activity_log(config)

    # User feedback
    reason = input_data.get('reason', 'unknown')
    incomplete_count = len(analysis['todos']['incomplete'])

    print(f"\n📊 Session ended ({reason})", file=sys.stderr)
    print(f"   📝 {analysis['total_messages']} messages exchanged", file=sys.stderr)

    if analysis['tool_calls']:
        total_tools = sum(analysis['tool_calls'].values())
        print(f"   🔧 {total_tools} tool call(s)", file=sys.stderr)

    if incomplete_count > 0:
        print(f"   ⚠️  {incomplete_count} task(s) incomplete", file=sys.stderr)

    if archive_file:
        print(f"   💾 Summary saved", file=sys.stderr)

    exit_allow()

if __name__ == '__main__':
    import sys
    try:
        main()
    except Exception as e:
        print(f"SessionEnd error: {e}", file=sys.stderr)
        exit_allow()  # Fail-open
