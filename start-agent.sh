#!/bin/bash
# Script to start an opencode agent with all repository skills loaded
cd "$(dirname "$0")"

echo "Loading all repository skills..."
# Auto-discover and load all skills in the skills directory
if [ -d "./.opencode/skills/" ]; then
    for skill_dir in ./.opencode/skills/*/; do
        if [ -d "$skill_dir" ]; then
            skill_name=$(basename "$skill_dir")
            echo "Loading skill: $skill_name"
            opencode skill load "$skill_name"
        fi
    done
fi

echo "Starting agent session with all repository skills loaded..."
# Start your agent here - replace this with actual agent command
# Example: opencode agent start --name research-agent
echo "Agent started with all repository skills loaded"