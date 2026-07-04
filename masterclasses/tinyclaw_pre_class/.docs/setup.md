# Setup Guide: Build a TinyClaw-Style Python Project From Scratch

This guide explains how to create a Python project like TinyClaw manually, without relying on a coding agent. The project is a local personal assistant that:

- runs as a Telegram bot,
- calls Anthropic through LangChain,
- supports tool use through a simple skills system,
- stores conversation sessions in JSON,
- stores simple long-term memory in JSON,
- loads a system prompt/personality from `SOUL.md`.

The examples below use `uv`, a `src/` layout, and Python 3.13.

## 1. Install prerequisites

Install:

- Python 3.13 or newer
- `uv`
- a Telegram bot token from BotFather
- an Anthropic API key

Check your tools:

```bash
python3 --version
uv --version
```

If `uv` is missing, install it from the official installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2. Create the project folder

```bash
mkdir tinyclaw
cd tinyclaw
uv init
```

Create the app layout:

```bash
mkdir -p src/skills/datetime
mkdir -p src/skills/memory
mkdir -p src/skills/browser
mkdir -p .docs
```

The final structure should look like this:

```text
tinyclaw/
  .docs/
  src/
    main.py
    agent_runtime.py
    context_builder.py
    memory_store.py
    session_manager.py
    skill_loader.py
    telegram_channel.py
    skills/
      datetime/
        SKILL.md
        handler.py
      memory/
        SKILL.md
        handler.py
      browser/
        SKILL.md
        handler.py
  SOUL.md
  .env
  .env.example
  .gitignore
  pyproject.toml
```

## 3. Add dependencies

Install the packages used by this project:

```bash
uv add langchain langchain-anthropic langchain-openai langchain-google-genai langgraph
uv add python-dotenv python-telegram-bot pydantic requests playwright
```

Install Playwright's browser runtime:

```bash
uv run playwright install chromium
```

## 4. Configure environment variables

Create `.env.example`:

```bash
touch .env.example
```

Add:

```text
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-opus-4-6
```

Create your local `.env`:

```bash
cp .env.example .env
```

Fill in the real values:

```text
ANTHROPIC_API_KEY=your_anthropic_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-opus-4-6
```

Keep `.env` private. Do not commit it.

## 5. Add `.gitignore`

Create `.gitignore`:

```text
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.DS_Store
.env
TINY_MEMORY.json
TINY_SESSIONS.json
```

## 6. Create the assistant personality file

Create `SOUL.md` in the project root:

```markdown
# Soul

You are TinyClaw, a personal AI assistant running on the user's own machine.
You have access to tools provided by installed skills.

## Personality

- Friendly, concise, and occasionally funny
- Use a casual tone like when texting a smart friend
- When unsure, say so honestly rather than making facts up

## Rules

- When saving notes, use short consistent keys like "name", "location", "job"
- Use available tools when they help
- Never run destructive commands without asking first
- Keep responses under 300 words unless asked for detail
```

## 7. Build the memory store

Create `src/memory_store.py`:

```python
import json
import os


class Memory:
    def __init__(self, path="TINY_MEMORY.json"):
        self.path = path

        if os.path.exists(path):
            with open(path) as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def get(self, key):
        return self._data.get(key)

    def keys(self):
        return list(self._data.keys())

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, default=str)
```

This gives the assistant a simple local key-value memory.

## 8. Build the session manager

Create `src/session_manager.py`:

```python
import json
import os
import time


class SessionManager:
    def __init__(self, path="TINY_SESSIONS.json"):
        self.path = path

        if os.path.exists(path):
            with open(path) as f:
                self.sessions = json.load(f)
        else:
            self.sessions = {}

    def get_or_create_session(self, client_id, channel):
        session_id = f"{channel}:{client_id}"

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "client_id": client_id,
                "channel": channel,
                "created_at": time.time(),
                "history": [],
            }

        return session_id

    def add_message(self, session_id, message):
        session = self.sessions.get(session_id)
        if session:
            session["history"].append(message)
            self._save()

    def get_history(self, session_id):
        session = self.sessions.get(session_id)
        return session["history"] if session else []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.sessions, f, indent=2, default=str)
```

This stores chat history per channel and user.

## 9. Build the context builder

Create `src/context_builder.py`:

```python
import os
from datetime import datetime, timezone


BASE_PROMPT = """You are a helpful personal AI assistant powered by TinyClaw.
Be concise, friendly, and helpful. Use tools when they would help."""


def load_soul():
    project_root = os.path.dirname(os.path.dirname(__file__))
    soul_path = os.path.join(project_root, "SOUL.md")

    try:
        with open(soul_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return BASE_PROMPT


def build_system_prompt(active_skills, memory=None):
    prompt = load_soul()

    if active_skills:
        prompt += "\n\n## Available Skills\n"
        for skill in active_skills:
            prompt += f"### {skill['name']}\n"
            prompt += f"{skill['description']}\n\n"

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
```

This combines the personality file, available skills, memory, and current time into one system prompt.

## 10. Build the skill loader

Create `src/skill_loader.py`:

```python
import importlib.util
import os


class SkillLoader:
    def __init__(self):
        self.skills = {}

    def load_from_directory(self, skills_dir):
        if not os.path.isdir(skills_dir):
            print("No Skills directory found.")
            return

        for entry in os.listdir(skills_dir):
            skill_dir = os.path.join(skills_dir, entry)
            skill_md = os.path.join(skill_dir, "SKILL.md")
            handler_py = os.path.join(skill_dir, "handler.py")

            if not os.path.isdir(skill_dir):
                continue
            if not os.path.exists(skill_md) or not os.path.exists(handler_py):
                continue

            try:
                with open(skill_md) as f:
                    name, description = self._parse_skill_md(f.read())

                spec = importlib.util.spec_from_file_location(f"skill_{entry}", handler_py)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                self.skills[name] = {
                    "name": name,
                    "description": description,
                    "tools": getattr(module, "tools", []),
                    "execute": getattr(module, "execute", None),
                }

                print(f"Skill Loaded: {name}")

            except Exception as e:
                print(f"Failed to load {entry}: {e}")

    def get_active_skills(self):
        return [
            {"name": s["name"], "description": s["description"]}
            for s in self.skills.values()
        ]

    def get_tools(self):
        tools = []

        for skill in self.skills.values():
            tools.extend(skill["tools"])

        return tools

    async def execute_tool(self, tool_name, tool_input, context):
        for skill in self.skills.values():
            if any(t["name"] == tool_name for t in skill["tools"]):
                if skill["execute"]:
                    return await skill["execute"](tool_name, tool_input, context)

        return {"error": f"Unknown tool: {tool_name}"}

    def _parse_skill_md(self, content):
        name = "unknown"
        description = ""

        for line in content.split("\n"):
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip()

        return name, description
```

Each skill folder needs:

- `SKILL.md` for name and description
- `handler.py` for tool schemas and execution

## 11. Build the agent runtime

Create `src/agent_runtime.py`:

```python
import json
from langchain_anthropic import ChatAnthropic
from context_builder import build_system_prompt


MAX_TOOL_ROUNDS = 5


class AgentRuntime:
    def __init__(self, provider, model, api_key, skills, memory):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.skills = skills
        self.memory = memory

    async def run(self, history, session_id, callbacks):
        on_token = callbacks.get("on_token")
        on_tool_use = callbacks.get("on_tool_use")

        system_prompt = build_system_prompt(self.skills.get_active_skills(), self.memory)
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        tools = self.skills.get_tools()

        response = ""
        rounds = 0

        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1

            result = await self._call_anthropic(
                system_prompt=system_prompt,
                messages=messages,
                tools=tools if tools else None,
            )

            if result["tool_calls"]:
                messages.append({"role": "assistant", "content": result["raw_content"]})

                for tool_call in result["tool_calls"]:
                    if on_tool_use:
                        await on_tool_use(tool_call["name"], tool_call["input"])

                    tool_result = await self.skills.execute_tool(
                        tool_call["name"],
                        tool_call["input"],
                        {"session_id": session_id, "memory": self.memory},
                    )

                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_call["id"],
                            "content": json.dumps(tool_result),
                        }],
                    })

                continue

            if result["text"]:
                if on_token:
                    await on_token(result["text"])
                response = result["text"]

            break

        return response

    async def _call_anthropic(self, system_prompt, messages, tools):
        llm = ChatAnthropic(
            model_name=self.model,
            max_tokens_to_sample=4096,
            api_key=self.api_key,
            timeout=120,
        )

        if tools:
            llm = llm.bind_tools([{
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            } for t in tools])

        result = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            *messages,
        ])

        raw_content = result.content
        if isinstance(raw_content, str):
            raw_content = [{"type": "text", "text": raw_content}]

        text_parts = []
        tool_calls = []

        for block in raw_content:
            if block["type"] == "text":
                text_parts.append(block.get("text") or "")
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "name": block["name"],
                    "input": block["input"],
                })

        if not tool_calls:
            for tool_call in getattr(result, "tool_calls", []) or []:
                tool_calls.append({
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "input": tool_call.get("args", {}),
                })

        return {
            "text": "".join(text_parts),
            "tool_calls": tool_calls or None,
            "raw_content": raw_content,
        }
```

This is the agent's loop:

1. Build a system prompt.
2. Send history and tool schemas to Anthropic.
3. If the model asks for a tool, execute it.
4. Feed the tool result back to the model.
5. Stop when the model returns a normal text response.

## 12. Create the Telegram channel

Create `src/telegram_channel.py`:

```python
import asyncio
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters


class TelegramChannel:
    def __init__(self, token, agent, sessions):
        self.token = token
        self.agent = agent
        self.sessions = sessions

    async def start(self):
        app = Application.builder().token(self.token).build()
        app.add_handler(MessageHandler(filters.TEXT, self._on_message))

        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        await asyncio.Future()

    async def _on_message(self, update: Update, context):
        chat_id = str(update.effective_chat.id)
        user_text = update.message.text

        if not user_text:
            return

        session_id = self.sessions.get_or_create_session(chat_id, "telegram")

        self.sessions.add_message(session_id, {
            "role": "user",
            "content": user_text,
            "timestamp": time.time(),
        })

        await update.effective_chat.send_action("typing")

        try:
            history = self.sessions.get_history(session_id)
            full_response = ""

            async def on_token(token):
                nonlocal full_response
                full_response += token

            async def on_tool_use(name, input):
                await update.effective_chat.send_action("typing")

            await self.agent.run(history, session_id, {
                "on_token": on_token,
                "on_tool_use": on_tool_use,
            })

            if full_response:
                for i in range(0, len(full_response), 4096):
                    await update.message.reply_text(full_response[i:i + 4096])

            self.sessions.add_message(session_id, {
                "role": "assistant",
                "content": full_response,
                "timestamp": time.time(),
            })

        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
```

This connects Telegram messages to the agent runtime.

## 13. Create the skills

### Datetime skill

Create `src/skills/datetime/SKILL.md`:

```markdown
---
name: datetime
description: Get the current date and time.
---
```

Create `src/skills/datetime/handler.py`:

```python
from datetime import datetime, timezone


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


async def execute(tool_name, tool_input, context):
    if tool_name == "get_current_datetime":
        now = datetime.now(timezone.utc)
        return {
            "readable": now.strftime("%A, %B %d, %Y %I:%M:%S %p UTC"),
        }

    return {"error": f"Unknown tool: {tool_name}"}
```

### Memory skill

Create `src/skills/memory/SKILL.md`:

```markdown
---
name: memory
description: Save a note to the user's personal memory.
---
```

Create `src/skills/memory/handler.py`:

```python
tools = [
    {
        "name": "save_note",
        "description": "Save a note or fact about the user to memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short descriptive key"},
                "content": {"type": "string", "description": "Note content"},
            },
            "required": ["key", "content"],
        },
    },
]


async def execute(tool_name, tool_input, context):
    memory = context["memory"]

    if tool_name == "save_note":
        memory.set(f"note:{tool_input['key']}", {
            "content": tool_input["content"],
        })

        return {"success": True, "key": tool_input["key"]}

    return {"error": f"Unknown tool: {tool_name}"}
```

### Browser skill

Create `src/skills/browser/SKILL.md`:

```markdown
---
name: browser
description: Browse the web, extract text from webpages, click elements, and fill and submit forms. Use when the user asks to visit a website, read a page, or interact with web content.
---
```

Create `src/skills/browser/handler.py`:

```python
from playwright.async_api import async_playwright


tools = [
    {
        "name": "browse_url",
        "description": "Navigate to a URL and return the page title and text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to visit"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "click_element",
        "description": "Click an element on the page by CSS selector or text.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector or text content, for example button.submit or text=Sign In",
                },
            },
            "required": ["selector"],
        },
    },
    {
        "name": "fill_input",
        "description": "Type text into an input field.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the input"},
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "get_page_content",
        "description": "Get the text content of the current page or a specific element.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "Optional CSS selector. If empty, returns full page text.",
                },
            },
            "required": [],
        },
    },
]

_browser = None
_page = None


async def _get_page():
    global _browser, _page

    if _browser and _page:
        return _page

    pw = await async_playwright().start()
    _browser = await pw.chromium.launch(headless=True)
    _page = await _browser.new_page()

    return _page


async def execute(tool_name, tool_input, context):
    try:
        page = await _get_page()

        if tool_name == "browse_url":
            url = tool_input["url"]

            if not url.startswith("http"):
                url = "https://" + url

            await page.goto(url, wait_until="domcontentloaded", timeout=10000)

            title = await page.title()
            text = await page.inner_text("body")

            return {
                "title": title,
                "url": page.url,
                "content_preview": text.strip()[:3000],
            }

        if tool_name == "click_element":
            await page.click(tool_input["selector"], timeout=3000)
            await page.wait_for_load_state("domcontentloaded")

            return {
                "clicked": tool_input["selector"],
                "new_url": page.url,
                "new_title": await page.title(),
            }

        if tool_name == "fill_input":
            await page.fill(tool_input["selector"], tool_input["text"])

            return {
                "filled": tool_input["selector"],
                "text": tool_input["text"],
            }

        if tool_name == "get_page_content":
            selector = tool_input.get("selector") or "body"
            text = await page.inner_text(selector)

            return {
                "url": page.url,
                "content": text.strip()[:5000],
            }

        return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}
```

## 14. Create the entry point

Create `src/main.py`:

```python
import asyncio
import os
from dotenv import load_dotenv
from memory_store import Memory
from session_manager import SessionManager
from skill_loader import SkillLoader
from agent_runtime import AgentRuntime
from telegram_channel import TelegramChannel


load_dotenv()


async def main() -> None:
    print("TinyClaw starting up...")

    memory = Memory()
    sessions = SessionManager()

    skills = SkillLoader()
    skills.load_from_directory(os.path.join(os.path.dirname(__file__), "skills"))

    agent = AgentRuntime(
        provider=os.getenv("MODEL_PROVIDER"),
        model=os.getenv("MODEL_NAME"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        skills=skills,
        memory=memory,
    )

    telegram = TelegramChannel(
        token=os.getenv("TELEGRAM_BOT_TOKEN"),
        agent=agent,
        sessions=sessions,
    )

    print("TinyClaw is running on Telegram.")

    await telegram.start()


if __name__ == "__main__":
    asyncio.run(main())
```

## 15. Run the project

Start the bot:

```bash
uv run src/main.py
```

You should see the skills load and the Telegram bot start polling. Open Telegram, find your bot, and send it a message.

## 16. Test common pieces manually

Check syntax:

```bash
uv run python -m py_compile src/*.py src/skills/*/*.py
```

Check that skills load:

```bash
PYTHONPATH=src uv run python -c "from skill_loader import SkillLoader; s=SkillLoader(); s.load_from_directory('src/skills'); print(s.get_tools())"
```

Check that the system prompt builds:

```bash
PYTHONPATH=src uv run python -c "from skill_loader import SkillLoader; from memory_store import Memory; from context_builder import build_system_prompt; s=SkillLoader(); s.load_from_directory('src/skills'); print(build_system_prompt(s.get_active_skills(), Memory())[:1000])"
```

## 17. Common issues

If the bot does not start, check:

- `.env` exists and contains `TELEGRAM_BOT_TOKEN`
- `.env` contains `ANTHROPIC_API_KEY`
- `MODEL_NAME` is set
- Playwright Chromium is installed with `uv run playwright install chromium`
- the imports work with `uv run src/main.py`

If the model does not use tools, check:

- each skill folder has both `SKILL.md` and `handler.py`
- each handler has a top-level `tools` list
- each handler has an async `execute(tool_name, tool_input, context)` function
- tool schemas use valid JSON Schema under the `parameters` key

If memory does not appear in the prompt, check:

- notes are saved with keys like `note:name`
- `Memory.keys()` returns those keys
- `build_system_prompt()` receives the same `Memory` instance used by the skills

## 18. Suggested next improvements

After the basic project works, improve it by:

- adding tests for `SkillLoader`, `Memory`, and `SessionManager`
- validating required environment variables before startup
- adding graceful shutdown for the Playwright browser
- limiting stored session history so prompts do not grow forever
- moving JSON data files into a dedicated `data/` folder
- adding structured logging instead of `print`
- updating `.env.example` whenever a new environment variable is required
