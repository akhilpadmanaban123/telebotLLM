import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from utils.config import TELEGRAM_TOKEN

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramBot, cls).__new__(cls)
            cls._instance.application = Application.builder().token(TELEGRAM_TOKEN).build()
        return cls._instance

    def add_handler(self, handler):
        self._instance.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    def schedule_task(self, callback, interval, first=0):
        job_queue = self._instance.application.job_queue
        job_queue.run_repeating(callback, interval=interval, first=first)

    def run(self):
        self._instance.application.run_polling()
