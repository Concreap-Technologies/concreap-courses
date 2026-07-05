import os
from datetime import datetime, timezone

BASE_PROMPT = """You are a helpful personal AI assistant powered by TinyClaw.
Be concise, friendly, and helpful. Use tools when they would help.
"""

#load SOUL.md
def load_soul():
    soul_path = os.path.join(os.path.dirname(__file__), "SOUL.md")

    try:
        with open(soul_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return BASE_PROMPT

# Combine soul, skills, user memory, current date and time into a single system prompt  
def build_context(active_skills, memory=None):
    prompt = load_soul()

    if active_skills:
        prompt += "\n\n## Available Skills\n"

        for skill in active_skills:
            prompt += f"### {skill["name"]}\n"
            prompt += f"{skill["description"]}\n"

    if memory:
        prefix = "note:"

        notes = {
            k[len(prefix):]: memory.get(k)
            for k in memory.keys()
            if k.startswith(prefix)
        }

        if notes:
            prompt += "\n\n## What you know about the user\n"
            for key, value in notes.items():
                content = value.get("content", value) if isinstance(value, dict) else value
                prompt += f"- {key}: {content}\n"

        prompt += f"\nCurrent time: {datetime.now(timezone.utc).isoformat()}"

        return prompt
    