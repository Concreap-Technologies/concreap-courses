import time
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from session import SessionManager
from agent import Agent

class Telegram:
    def __init__(self, token, agent: Agent, sessions: SessionManager):
        self.token = token
        self.agent = agent
        self.sessions = sessions

    async def start(self):

        # Build the telegram bot app
        app = Application.builder().token(self.token).build()

        # Listen for messages from the user and route them to on_message
        app.add_handler(MessageHandler(filters.TEXT, self.on_message))

        # Initialize the bot and start checking for new messages
        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        # Keep the bot running forever
        await asyncio.Future()

    async def on_message(self, update: Update, context):
        # Get the user's unique ID
        chat_id = str(update.effective_chat.id)

        # Get the text or message the user sent
        user_text = update.message.text

        # Ignore empty messages
        if not user_text:
            return
        
        # Find or create a new session per telegram chat
        session_id = self.sessions.find_or_create(chat_id, "telegram")

        # Save user message to the session history
        self.sessions.add_message(session_id, {
            "role": "user",
            "content": user_text,
            "timestamp": time.time()
        })

        # Show "typing..." indicator in Telegram
        await update.effective_chat.send_action("typing")

        try:
            # Get the full conversation history for this user
            history = self.sessions.get_history(session_id)

            full_response = ""

            # Callback: on_token -> LLM calls for each response it generates
            async def on_token(token):
                nonlocal full_response
                full_response += token

            # Callback: on_tool_use -> Refresh the typing indicator when the agent uses a tool
            async def on_tool_use(name, input):
                await update.effective_chat.send_action("typing")

            # Run the ReAct loop
            await self.agent.run(history, session_id, {
                "on_token": on_token,
                "on_tool_use": on_tool_use
            })

            if not full_response:
                full_response = "I ran into an issue and couldn't generate a response. Please try again."

            # Send the full reply back to the user on telegram
            if full_response:
                for i in range(0, len(full_response), 4096):
                    await update.message.reply_text(full_response[i:i+4096])
            
            # Save the LLM response to session history
            self.sessions.add_message(session_id, {
                "role": "assistant",
                "content": full_response,
                "timestamp": time.time()
            })

        except Exception as e:
            print(e)
            await update.message.reply_text(f"Error: ${e}")
