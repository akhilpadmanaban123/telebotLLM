from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes

class Functionality(ABC):
    @abstractmethod
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass
