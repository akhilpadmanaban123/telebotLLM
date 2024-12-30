import asyncio
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from functionalities.base import Functionality
from utils.config import gemini_model

logger = logging.getLogger(__name__)

class ReminderFunctionality(Functionality):
    def __init__(self):
        self.reminders = {}

    async def set_reminder(self, chat_id, reminder_time, reminder_text, context):
        now = datetime.now()
        delay = (reminder_time - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            await self.send_reminder(chat_id, reminder_text, context)
        else:
            logger.warning("Reminder time is in the past.")

    async def send_reminder(self, chat_id, reminder_text, context):
        await context.bot.send_message(chat_id=chat_id, text=f"⏰ Reminder: {reminder_text}")

    async def parse_reminder_input(self, user_input):
        try:
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
            response = gemini_model.generate_content(prompt)
            response_text = response.text.strip()
            logger.info(f"Raw response from Gemini: {response_text}")
            reminder_data = json.loads(response_text)
            time_str = reminder_data.get("time", "")
            date_str = reminder_data.get("date", datetime.now().strftime("%Y-%m-%d"))
            content = reminder_data.get("content", "")
            reminder_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M %p")
            return reminder_time, content
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Gemini: {response_text}")
            return None, None
        except Exception as e:
            logger.error(f"Error parsing reminder input: {e}")
            return None, None

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_input = update.message.text
        if not user_input:
            await update.message.reply_text("Please provide a reminder.")
            return
        reminder_time, reminder_text = await self.parse_reminder_input(user_input)
        if not reminder_time or not reminder_text:
            await update.message.reply_text("Sorry, I couldn't understand your reminder. Please try again.")
            return
        asyncio.create_task(self.set_reminder(update.message.chat_id, reminder_time, reminder_text, context))
        await update.message.reply_text(f"Reminder set for {reminder_time.strftime('%Y-%m-%d %I:%M %p')}: {reminder_text}")
