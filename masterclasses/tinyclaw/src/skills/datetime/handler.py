from datetime import datetime, timezone

# Tool Definition (Schema)
tools = [
    {
        "name": "get_current_datetime",
        "description": "Get the current date and time.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# Tool Execution (Execution Function)
async def execute(tool_name, tool_input, context):
    if tool_name == "get_current_datetime":
        now = datetime.now(timezone.utc)

        return {
            "readable": now.strftime("%A %B %d, %Y %I:%M:%S %p UTC")
        }
    
    return { "error": f"unknown tool: {tool_name}" }