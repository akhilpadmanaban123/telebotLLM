import logging
from functionalities.base import Functionality
from telegram import Update
from telegram.ext import ContextTypes
from utils.config import gemini_model

logger = logging.getLogger(__name__)

class ChatFunctionality(Functionality):
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        try:
            response = gemini_model.generate_content(user_message)
            await update.message.reply_text(response.text)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            await update.message.reply_text("Sorry, I couldn't process your message. Please try again.")
