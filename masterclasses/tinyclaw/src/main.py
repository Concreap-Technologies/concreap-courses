import asyncio
import os
from dotenv import load_dotenv
from memory import Memory
from session import SessionManager
from skills import SkillLoader
from agent import Agent
from telegram_bot import Telegram

load_dotenv()

async def main() -> None:

    print("TinyClaw starting up...")

    # Create memory
    memory = Memory()

    # Create session manager
    sessions = SessionManager()

    # Load all skills
    skills = SkillLoader()
    skills.load_from_directory(os.path.join(os.path.dirname(__file__), "skills"))

    # Create the agent runtime
    agent = Agent(
        provider=os.getenv("MODEL_PROVIDER"),
        model=os.getenv("MODEL_NAME"),
        api_key=os.getenv("GEMINI_API_KEY"),
        skills=skills,
        memory=memory
    )

    # Create the telegra channel and connect it to the agent and sessions
    telegram = Telegram(
        token=os.getenv("TELEGRAM_BOT_TOKEN"),
        agent=agent,
        sessions=sessions
    )

    print("\nTinyClaw is running on Telegram")
    print("\nGo CLAW!!!")

    # Start the telegram bot
    await telegram.start()

if __name__ == "__main__":
    asyncio.run(main())


