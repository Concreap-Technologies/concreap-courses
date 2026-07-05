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

## 6. Create all the files needed

```bash
# Create project folder
mkdir tiny-openclaw && cd tiny-openclaw

# Create folders for skills and frontend
mkdir -p skills/datetime skills/memory_work skills/browser_use

# Create core component files
touch main.py agent_runtime.py context_builder.py session_manager.py telegram_channel.py memory_store.py skill_loader.py SOUL.md .env

# Create datetime skill files
touch skills/datetime/SKILL.md skills/datetime/handler.py

# Create memory note skill files
touch skills/memory_work/SKILL.md skills/memory_work/handler.py

# Create Browser use skill files
touch skills/browser_use/SKILL.md skills/browser_use/handler.py
```

## 7. Build Memory
``` bash
# Download the Chromium browser binary that Playwright needs for the Browser use skill
playwright install chromium
```
## 8. Build Session Manager
## 9. Setup and build SKILLs

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
