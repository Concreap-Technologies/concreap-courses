from datetime import datetime, timezone

# Tool definition to tell the agent about the available 'get_current_datetime' tool
tools = [
    {
        "name": "get_current_datetime",
        "description": "Get the current date and time.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }
]

# Function called when the agent invokes this tool
async def execute(tool_name, tool_input, context):
    if tool_name == "get_current_datetime":
        # Get the current date and time
        now = datetime.now(timezone.utc)

        # Return a human-readable format 
        return {
            "readable": now.strftime("%A, %B %d, %Y %I:%M:%S %p UTC"),
        }

    return {"error": f"Unknown tool: {tool_name}"}