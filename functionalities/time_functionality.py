import asyncio
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from functionalities.base import Functionality
from utils.config import gemini_model

class TimeFunctionality(Functionality):
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        current_time = datetime.now().strftime("%I:%M %p")
        current_date = datetime.now().strftime("%Y-%m-%d")
        animated_image_url = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
        formatted_text = (
            "*🕒 Time*\n"
            f"`{current_time}`\n\n"
            "*📅 Date*\n"
            f"`{current_date}`"
        )
        await context.bot.send_animation(
            chat_id=update.message.chat_id,
            animation=animated_image_url,
            caption=formatted_text,
            parse_mode="MarkdownV2"
        )
