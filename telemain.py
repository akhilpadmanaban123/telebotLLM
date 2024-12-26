import logging
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import asyncio
from datetime import datetime
import google.generativeai as genai  # Gemini API
from abc import ABC, abstractmethod  # Import ABC and abstractmethod

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your API keys
TELEGRAM_TOKEN = "7551480728:AAHXUv-sSrkjluC-Ehubaj1OjUevLRYUbzk"
GEMINI_API_KEY = "AIzaSyBulnqflbB3SRzg4bR-wnG648jVACQGJ2g"

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# Singleton class for the Telegram Bot
class TelegramBot:
    _instance = None

    def __new__(cls, token):
        if cls._instance is None:
            cls._instance = super(TelegramBot, cls).__new__(cls)
            cls._instance.application = Application.builder().token(token).build()
        return cls._instance

    def add_handler(self, handler):
        self._instance.application.add_handler(handler)

    def run(self):
        self._instance.application.run_polling()

# Abstract base class for functionalities
class Functionality(ABC):
    @abstractmethod
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

# Reminder functionality
class ReminderFunctionality(Functionality):
    def __init__(self):
        self.reminders = {}

    async def set_reminder(self, chat_id, reminder_time, reminder_text):
        now = datetime.now()
        delay = (reminder_time - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            await self.send_reminder(chat_id, reminder_text)
        else:
            logger.warning("Reminder time is in the past.")

    async def send_reminder(self, chat_id, reminder_text, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=chat_id, text=f"⏰ Reminder: {reminder_text}")

    async def parse_reminder_input(self, user_input):
        """
        Use Gemini API to extract time, date, and content from the user's input.
        """
        try:
            # Improved prompt for Gemini
            prompt = (
                f"Extract the time, date, and content for a reminder from the following text:\n"
                f"'{user_input}'\n"
                "Return the response **only** in JSON format with keys: 'time', 'date', 'content'.\n"
                "Rules:\n"
                "1. Time can be in any format (e.g., '12:17', '12:18am', '12:19 AM'). Convert it to 'HH:MM AM/PM' format.\n"
                "2. Date can be in any format (e.g., '27-12-2024', 'today', 'tomorrow'). Convert it to 'YYYY-MM-DD' format.\n"
                "3. If the date is not mentioned, assume it is today.\n"
                "4. Content is the reminder message. If not explicitly mentioned, infer it from the context.\n"
                "Example output: {{\"time\": \"12:19 AM\", \"date\": \"2024-12-27\", \"content\": \"Eat food\"}}\n"
                "Do not include any additional text or explanations. Only return valid JSON."
            )

            # Send the prompt to Gemini
            response = gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            # Debugging: Log the raw response from Gemini
            logger.info(f"Raw response from Gemini: {response_text}")

            # Parse the JSON response
            import json
            reminder_data = json.loads(response_text)

            # Extract time, date, and content
            time_str = reminder_data.get("time", "")
            date_str = reminder_data.get("date", datetime.now().strftime("%Y-%m-%d"))
            content = reminder_data.get("content", "")

            # Combine date and time into a datetime object
            reminder_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M %p")

            return reminder_time, content

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Gemini: {response_text}")
            return None, None
        except Exception as e:
            logger.error(f"Error parsing reminder input: {e}")
            return None, None
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_input = update.message.text  # Get the user's input
        print(user_input)
        if not user_input:
            await update.message.reply_text("Please provide a reminder.")
            return

        # Parse the user's input using Gemini
        reminder_time, reminder_text = await self.parse_reminder_input(user_input)

        if not reminder_time or not reminder_text:
            await update.message.reply_text("Sorry, I couldn't understand your reminder. Please try again.")
            return

        # Schedule the reminder
        asyncio.create_task(self.set_reminder(update.message.chat_id, reminder_time, reminder_text))
        await update.message.reply_text(f"Reminder set for {reminder_time.strftime('%Y-%m-%d %I:%M %p')}: {reminder_text}")

# Time functionality
class TimeFunctionality(Functionality):
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Fetch the current time and date
        current_time = datetime.now().strftime("%I:%M %p")  # Time in 12-hour format
        current_date = datetime.now().strftime("%Y-%m-%d")  # Date in YYYY-MM-DD format

        # URL to the animated image (GIF)
        animated_image_url = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"  # Replace with your GIF URL

        # Formatted text with MarkdownV2
        formatted_text = (
            "*🕒 Current Time*\n"
            f"`{current_time}`\n\n"  # Monospace for time
            "*📅 Current Date*\n"
            f"`{current_date}`"  # Monospace for date
        )

        # Send the animated image with the formatted text
        await context.bot.send_animation(
            chat_id=update.message.chat_id,
            animation=animated_image_url,
            caption=formatted_text,
            parse_mode="MarkdownV2"  # Enable MarkdownV2 formatting
        )

# Chat functionality using Gemini
class ChatFunctionality(Functionality):
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        try:
            # Generate a response using Gemini
            response = gemini_model.generate_content(user_message)
            await update.message.reply_text(response.text)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            await update.message.reply_text("Sorry, I couldn't process your message. Please try again.")

# Factory class to create functionalities
class FunctionalityFactory:
    @staticmethod
    def create_functionality(name):
        if name == "remind":
            return ReminderFunctionality()
        elif name == "time":
            return TimeFunctionality()
        elif name == "chat":
            return ChatFunctionality()
        else:
            raise ValueError(f"Unknown functionality: {name}")

# Main function to start the bot
def main():
    # Create the bot instance
    bot = TelegramBot(TELEGRAM_TOKEN)

    # Create functionalities
    reminder_func = FunctionalityFactory.create_functionality("remind")
    time_func = FunctionalityFactory.create_functionality("time")
    chat_func = FunctionalityFactory.create_functionality("chat")

    # Message handler to decide which functionality to execute
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_input = update.message.text.lower()  # Convert input to lowercase for easier matching

        # Check if the input contains "remind" or "reminder"
        if "remind" in user_input or "reminder" in user_input:
            await reminder_func.execute(update, context)
        # Check if the input is asking for the current time
        elif "time" in user_input or "what's the time" in user_input or "current time" in user_input:
            await time_func.execute(update, context)
        # Default to chat functionality
        else:
            await chat_func.execute(update, context)

    # Add message handler
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    bot.run()

if __name__ == "__main__":
    main()
