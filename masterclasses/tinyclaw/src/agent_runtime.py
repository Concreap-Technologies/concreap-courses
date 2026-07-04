import json
from langchain_anthropic import ChatAnthropic
from context_builder import build_system_prompt

# Max times the agent can call tools before stopping
MAX_TOOL_ROUNDS = 5

class AgentRuntime:
    def __init__(self, provider, model, api_key, skills, memory):
        self.provider = provider  # LLM provider (we use "anthropic")
        self.model = model        # LLM to use (we use "claude-opus-4-6")
        self.api_key = api_key    # API key for the LLM provider
        self.skills = skills      # Skill loader instance
        self.memory = memory      # Memory store instance

    async def run(self, history, session_id, callbacks):
        # Callback to send the final response to the user (Defined in ./telegram_channel.py)
        on_token = callbacks.get("on_token")

        # Callback to notify the user when a tool is being used (Defined in ./telegram_channel.py)
        on_tool_use = callbacks.get("on_tool_use")

        # Build system prompt 
        system_prompt = build_system_prompt(self.skills.get_active_skills(), self.memory)

        # Convert session history to API message format
        messages = [{"role": m["role"], "content": m["content"]} for m in history]

        # Get tool definitions from all loaded skills
        tools = self.skills.get_tools()

        response = ""
        rounds = 0

        # ReAct loop that keeps going until LLM returns an answer or hits the limit
        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1

            # Send context to LLM and get a result
            result = await self._call_anthropic(
                system_prompt=system_prompt,
                messages=messages,
                tools=tools if tools else None,
            )

            # If the LLM wants to use tools, execute them and loop back
            if result["tool_calls"]:
                # Add the LLM's tool request to the conversation
                messages.append(
                    {"role": "assistant", "content": result["raw_content"]}
                )

                # Run each tool and feed the results back
                for tool_call in result["tool_calls"]:
                    if on_tool_use:
                        await on_tool_use(tool_call["name"], tool_call["input"])

                    # Execute the tool through the skill loader
                    tool_result = await self.skills.execute_tool(
                        tool_call["name"],
                        tool_call["input"],
                        {"session_id": session_id, "memory": self.memory},
                    )

                    # Add tool result to conversation history so the LLM 
                    # can see it in the next round
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_call["id"],
                            "content": json.dumps(tool_result),
                        }],
                    })

                continue  # Start the next loop with the new tool results added

            # If no tools needed, send the final response to the user
            if result["text"]:
                if on_token:
                    await on_token(result["text"])
                response = result["text"]
            
            # Exit once we have a final non-tool response
            break  

        return response

    # Call Anthropic through LangChain
    async def _call_anthropic(self, system_prompt, messages, tools):
        # Configure LangChain's Anthropic chat model with the same request params
        llm = ChatAnthropic(
            model_name=self.model,
            max_tokens_to_sample=4096,
            api_key=self.api_key,
            timeout=120,
        )

        # Add tool definitions for the loaded Skills using Anthropic's schema shape
        if tools:
            llm = llm.bind_tools([{
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            } for t in tools])

        # LangChain accepts the same role/content message shape used by this runtime.
        result = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            *messages,
        ])

        raw_content = result.content
        if isinstance(raw_content, str):
            raw_content = [{"type": "text", "text": raw_content}]

        text_parts = []
        tool_calls = []

        # Response can contain text blocks, "tool_use" blocks, or both
        for block in raw_content:
            if block["type"] == "text":
                text_parts.append(block.get("text") or "")
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "name": block["name"],
                    "input": block["input"],
                })

        # Some LangChain integrations also expose parsed tool calls separately.
        if not tool_calls:
            for tool_call in getattr(result, "tool_calls", []) or []:
                tool_calls.append({
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "input": tool_call.get("args", {}),
                })

        # Return normalized output
        return {
            "text": "".join(text_parts),
            "tool_calls": tool_calls or None,
            "raw_content": raw_content,
        }
