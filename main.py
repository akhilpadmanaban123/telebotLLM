from bot import TelegramBot
from functionalities.reminder_functionality import ReminderFunctionality
from functionalities.time_functionality import TimeFunctionality
from functionalities.chat_functionality import ChatFunctionality
from functionalities.birthday_functionality import BirthdayFunctionality
from utils.config import FIREBASE_SERVICE_ACCOUNT_KEY
from utils.firebase import initialize_firebase

def main():
    # Initialize Firebase
    initialize_firebase(FIREBASE_SERVICE_ACCOUNT_KEY)

    # Create the bot instance
    bot = TelegramBot()

    # Create functionalities
    reminder_func = ReminderFunctionality()
    time_func = TimeFunctionality()
    chat_func = ChatFunctionality()
    birthday_func = BirthdayFunctionality()

    # Message handler to decide which functionality to execute
    async def handle_message(update, context):
        user_input = update.message.text.lower()  # Convert input to lowercase for easier matching

        # Check if the input contains "remind" or "reminder"
        if "remind" in user_input or "reminder" in user_input:
            await reminder_func.execute(update, context)
        # Check if the input is asking for the current time
        elif "time" in user_input or "what's the time" in user_input or "current time" in user_input:
            await time_func.execute(update, context)
        # Check if the input is related to birthdays
        elif "birthday" in user_input or "birthdays" in user_input:
            await birthday_func.execute(update, context)
        # Default to chat functionality
        else:
            await chat_func.execute(update, context)

    # Add message handler
    bot.add_handler(handle_message)

    # Schedule the birthday reminder task
    bot.schedule_task(
        birthday_func.check_upcoming_birthdays,
        interval=86400,  # Check every 24 hours
        first=10  # Start after 10 seconds
    )

    # Run the bot
    bot.run()

if __name__ == "__main__":
    main()
