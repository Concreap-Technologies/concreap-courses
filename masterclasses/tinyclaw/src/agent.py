import json
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage
from context import build_context

# Max times the agent can call tools or a tool before stopping
MAX_TOOL_ROUNDS = 5

class Agent:
    def __init__(self, provider, model, api_key, skills, memory):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.skills = skills
        self.memory = memory

    async def run(self, history, session_id, callbacks):
        # Callback to send the final response to the user
        on_token = callbacks.get("on_token")

        on_tool_use = callbacks.get("on_tool_use")

        # Grab system prompt fron contex
        system_prompt = build_context(self.skills.get_active_skills(), self.memory)

        # Convert session history to API message format
        messages = [
            {
                "role": m["role"],
                "content": m["content"]
            }
            for m in history
        ]

        # get tool definitions from all loaded skills
        tools = self.skills.get_tools()

        response = ""
        rounds = 0

        # ReAct loop that keeps going until LLM returns a final response or hist the limit
        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1

            # Send context to llm to get result
            result = await self.call_gemini(
                system_prompt=system_prompt,
                messages=messages,
                tools=tools if tools else None
            )

            # if llm wants to use tools, execute them and loop back
            if result["tool_calls"]:

                # Add the LLM's tool request to the conversation
                messages.append(result["message"])
                
                # Run each tool and feed the results back
                for tool_call in result["tool_calls"]:
                    if on_tool_use:
                        await on_tool_use(tool_call["name"], tool_call["input"])

                    try:
                        tool_result = await self.skills.execute_tool(
                            tool_call["name"],
                            tool_call["input"],
                            {
                                "session_id": session_id,
                                "memory": self.memory
                            }
                        )

                        messages.append(
                            ToolMessage(
                                content=json.dumps(tool_result, default=str),
                                tool_call_id=tool_call["id"]
                            )
                        )

                    except Exception as error:
                        messages.append(
                            ToolMessage(
                                content=json.dumps({
                                    "success": False,
                                    "error": str(error)
                                }),
                                tool_call_id=tool_call["id"],
                                status="error"
                            )
                        )

                continue # Start the next loop with the new tool result added

            # If there are no too requests, then return the response back to the user
            if result["text"]:
                if on_token:
                    await on_token(result["text"])
                response = result["text"]

            break # Exit once we have a final non-tool response

        return response

    async def call_anthropic(self, system_prompt, messages, tools):

        # configure and define llm using langchain
        llm = ChatAnthropic(
            model_name=self.model,
            max_tokens_to_sample=4096,
            api_key=self.api_key,
            timeout=120
        )

        # Let llm know the tools available
        if tools:
            llm = llm.bind_tools([{
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"]
            } for t in tools])

        # invoke llm to run
        result = await llm.ainvoke([
            { "role": "system", "content": system_prompt },
            *messages
        ])

        raw_content = result.content
        if isinstance(raw_content, str):
            raw_content = [
                { "type": "text", "text": raw_content }
            ]
        
        text_parts = []
        tool_calls = []

        for block in raw_content: 
            if block["type"] == "text":
                text_parts.append(block.get("text") or "")
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "name": block["name"],
                    "input": block["input"]
                })

        if not tool_calls:
            for tool_call in getattr(result, "tool_calls", []) or []:
                tool_calls.append({
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "input": tool_call.get("args", {})
                })

        return {
            "text": "".join(text_parts),
            "tool_calls": tool_calls or None,
            "raw_content": raw_content,
            "message": result
        }
    
    async def call_gemini(self, system_prompt, messages, tools):

        # configure and define llm using langchain
        llm = ChatGoogleGenerativeAI(
            model=self.model,
            max_tokens=4096,
            api_key=self.api_key,
            request_timeout=120
        )

        # Let llm know the tools available
        if tools:
            llm = llm.bind_tools([{
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"]
            } for t in tools])

        # invoke llm to run
        result = await llm.ainvoke([
            { "role": "system", "content": system_prompt },
            *messages
        ])

        raw_content = result.content
        if isinstance(raw_content, str):
            raw_content = [
                { "type": "text", "text": raw_content }
            ]
        
        text_parts = []
        tool_calls = []

        for block in raw_content: 
            if block["type"] == "text":
                text_parts.append(block.get("text") or "")
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "name": block["name"],
                    "input": block["input"]
                })

        if not tool_calls:
            for tool_call in getattr(result, "tool_calls", []) or []:
                tool_calls.append({
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "input": tool_call.get("args", {})
                })

        return {
            "text": "".join(text_parts),
            "tool_calls": tool_calls or None,
            "raw_content": raw_content,
            "message": result
        }