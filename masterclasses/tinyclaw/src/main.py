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

    # Create the Memory store
    memory = Memory()

    # Create the Session manager 
    sessions = SessionManager()

    # Load all Skills
    skills = SkillLoader()
    skills.load_from_directory(os.path.join(os.path.dirname(__file__), "skills"))

    # Create the agent runtime 
    agent = AgentRuntime(
        provider = os.getenv("MODEL_PROVIDER"),
        model = os.getenv("MODEL_NAME"),
        api_key = os.getenv("ANTHROPIC_API_KEY"), 
        skills = skills,
        memory = memory,
    )

    # Create the Telegram channel and connect it to the LLM agent and sessions
    telegram = TelegramChannel(
        token = os.getenv("TELEGRAM_BOT_TOKEN"),
        agent = agent,
        sessions = sessions,
    )

    print("\nTinyClaw is running on Telegram.")
    print("\nGO CLAW!!! 🦞🦞🦞")

    # Start the Telegram bot 
    await telegram.start()


if __name__ == "__main__":
    asyncio.run(main())
