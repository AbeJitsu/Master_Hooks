#!/bin/bash
# PostToolUse Hook: Logs all Write/Edit operations to activity log

# Read JSON input from stdin
input=$(cat)

# Extract file_path from tool_input
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
tool_name=$(echo "$input" | jq -r '.tool_name // empty')

# Only log if we have a file path
if [ -n "$file_path" ]; then
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    log_dir="$CLAUDE_PROJECT_DIR/.claude/hooks"
    log_file="$log_dir/activity.log"

    # Create log directory if it doesn't exist
    mkdir -p "$log_dir"

    # Log the operation
    echo "[$timestamp] $tool_name: $file_path" >> "$log_file"
fi

exit 0
