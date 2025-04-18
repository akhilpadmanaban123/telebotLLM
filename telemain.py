import logging, os, json, calendar
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai  # Gemini API
import firebase_admin  # Firebase
from firebase_admin import credentials, firestore  # Firebase Firestore
from tabulate import tabulate  # Make sure to install this with `pip install tabulate`
import asyncio
from abc import ABC, abstractmethod  # Import ABC and abstractmethod

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your API keys
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# JSON file to store birthdays
BIRTHDAYS_FILE = "Birthdays.json"


# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# Firebase setup
SERVICE_ACCOUNT_KEY = "D:/My Works/TelegramBot/telegrambotllm-firebase-adminsdk-6lsyf-b77d01b0b7.json"  # Replace with your service account key
cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
firebase_admin.initialize_app(cred)
db = firestore.client()

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

    async def set_reminder(self, chat_id, reminder_time, reminder_text, context: ContextTypes.DEFAULT_TYPE):
        now = datetime.now()
        delay = (reminder_time - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            await self.send_reminder(chat_id, reminder_text, context)
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
        if not user_input:
            await update.message.reply_text("Please provide a reminder.")
            return

        # Parse the user's input using Gemini
        reminder_time, reminder_text = await self.parse_reminder_input(user_input)

        if not reminder_time or not reminder_text:
            await update.message.reply_text("Sorry, I couldn't understand your reminder. Please try again.")
            return

        # Schedule the reminder
        asyncio.create_task(self.set_reminder(update.message.chat_id, reminder_time, reminder_text, context))
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
            "*🕒 Time*\n"
            f"`{current_time}`\n\n"  # Monospace for time
            "*📅 Date*\n"
            f"`{current_date}`"  # Monospace for date
        )

        # Send the animated image with the formatted text
        await context.bot.send_animation(
            chat_id=update.message.chat_id,
            animation=animated_image_url,
            caption=formatted_text,
            parse_mode="MarkdownV2"  # Enable MarkdownV2 formatting
        )

# Birthday functionality
class BirthdayFunctionality:
    def __init__(self):
        # Load existing birthdays from the JSON file
        self.birthdays = self._load_birthdays()

    def _load_birthdays(self):
        """
        Load birthdays from the JSON file.
        """
        if os.path.exists(BIRTHDAYS_FILE):
            with open(BIRTHDAYS_FILE, "r") as file:
                return json.load(file)
        return []

    def _save_birthdays(self):
        """
        Save birthdays to the JSON file.
        """
        with open(BIRTHDAYS_FILE, "w") as file:
            json.dump(self.birthdays, file, indent=4)

    async def parse_birthday_input(self, user_input):
        """
        Use Gemini API to extract name and birthdate from the user's input.
        Also, extract the month name from the birthdate.
        """
        try:
            # Prompt for Gemini to extract name and birthdate
            prompt = (
                f"Extract the name and birthdate from the following text:\n"
                f"'{user_input}'\n"
                "Rules:\n"
                "1. The name is the person whose birthday is being mentioned.\n"
                "2. The birthdate can be in any format (e.g., '20th December', '12/20/2000', 'December 20, 2000', '20-12-2000'). Convert it to 'YYYY-MM-DD' format.\n"
                "3. If the year is not mentioned, assume the current year.\n"
                "4. If the user provides a phrase like 'save the birthday of' or 'remember the birthday of', extract the name and birthdate from that context.\n"
                "5. If the user provides multiple names or dates, extract the first valid pair.\n"
                "6. Return the response **only** in JSON format with keys: 'name', 'birthdate'.\n"
                "Examples:\n"
                "Input: 'Save the birthday of Aadithya on 20th December'\n"
                "Output: {{\"name\": \"Aadithya\", \"birthdate\": \"2023-12-20\"}}\n"
                "Input: 'Remember that John's birthday is on 12/20/2000'\n"
                "Output: {{\"name\": \"John\", \"birthdate\": \"2000-12-20\"}}\n"
                "Input: 'Add Sarah's birthday: December 20, 1995'\n"
                "Output: {{\"name\": \"Sarah\", \"birthdate\": \"1995-12-20\"}}\n"
                "Input: 'Save the birthday of Alex as 20-12-2000'\n"
                "Output: {{\"name\": \"Alex\", \"birthdate\": \"2000-12-20\"}}\n"
                "Ensure the response is always valid JSON and does not contain any additional text."
            )

            # Send the prompt to Gemini
            response = gemini_model.generate_content(prompt)
            response_text = response.text.strip()
            print(response_text)
            # Extract the JSON part from the response
            start_index = response_text.find("{")
            end_index = response_text.rfind("}") + 1

            if start_index == -1 or end_index == -1:
                logger.error("No JSON object found in the response.")
                return None, None

            json_str = response_text[start_index:end_index]

            # Parse the JSON response
            birthday_data = json.loads(json_str)
            
            print(birthday_data)

            # Extract name and birthdate
            name = birthday_data.get("name", "")
            birthdate = birthday_data.get("birthdate", "")


            # Extract the month name from the birthdate
            if birthdate:
                try:
                    # Split the birthdate into day, month, and year
                    year,month,day = birthdate.split("-")

                    # Convert month number to month name
                    month_number = int(month)
                    month_name = calendar.month_name[month_number]
        
                    # Format the birthdate as "12-March-2024"
                    formatted_birthdate = f"{day}-{month_name}-{year}"
                    return name,formatted_birthdate
                except (IndexError, ValueError) as e:
                    logger.error(f"Error formatting birthdate: {e}")
                    return "Unknown"

        except Exception as e:
            logger.error(f"Error parsing birthday input: {e}")
            return None, None, None

    async def save_birthday(self, name, birthdate, chat_id):
        """
        Save the birthday to the JSON file.
        """
        try:
            # Add the new birthday to the list
            self.birthdays.append({
                "name": name,
                "birthdate": birthdate,
                "chat_id": chat_id
            })
            # Save the updated list to the JSON file
            self._save_birthdays()
            return True
        except Exception as e:
            logger.error(f"Error saving birthday: {e}")
            return False
    
    async def checkCondition(self, action):
        try:
            # Explicit prompt for Gemini
            prompt = (
                f"Respond only with 'true' or 'false' based on the following input:\n"
                f"{action}\n"
                "Rules:\n"
                "1. Return 'true' if the input clearly suggests the action.\n"
                "2. Return 'false' if the input does not suggest the action.\n"
                "3. Do not include any additional text or explanations.\n"
                "Example:\n"
                "Input: 'Save the birthday of Akhil on 6th April 2001'\n"
                "Output: true\n"
                "Input: 'What's the weather today?'\n"
                "Output: false"
                "input: 'Show all birthdays'\n"
                "Output: true"
            )

            # Send the prompt to Gemini
            response = self.invoke_gemini(prompt)
            response_text = response.strip().lower()

            # Debugging: Log the response from Gemini
            logger.info(f"Gemini response for action '{action}': {response_text}")

            # Return True if the response is 'true', otherwise False
            return response_text == 'true'
        except Exception as e:
            logger.error(f"Error checking condition: {e}")
            return False


    async def get_birthdays(self, chat_id):
        """
        Retrieve all birthdays from the JSON file and display them as a visually appealing table.
        """
        try:
            # Load all birthdays
            birthdays = self._load_birthdays()

            if not birthdays:
                return "🎉 No birthdays found."

            # Format the birthdays as a table
            table = tabulate(
                [(b["name"], b["birthdate"]) for b in birthdays],
                headers=["🎈 Name", "📅 Birthdate"],
                tablefmt="fancy_grid"  # Use a visually appealing table format
            )

            # Add a birthday-themed image URL
            image_url = "https://giphy.com/gifs/MickeyMouse-fun-excited-disney-Im6d35ebkCIiGzonjI"  # Replace with your image URL

            # Combine the table and image into a single message
            message = (
                f"🎉 All Birthdays:\n\n"
                f"{table}\n\n"
                f"🎂 Celebrate with joy! 🎉\n"
                f"{image_url}"
            )

            return message
        except Exception as e:
            logger.error(f"Error retrieving birthdays: {e}")
            return "❌ Failed to retrieve birthdays. Please try again."


    async def check_upcoming_birthdays(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Check for upcoming birthdays and send reminders 1 day before.
        """
        try:
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)

            for birthday in self.birthdays:
                if datetime.strptime(birthday["birthdate"], "%Y-%m-%d").date() == tomorrow:
                    await context.bot.send_message(
                        chat_id=birthday["chat_id"],
                        text=f"🎉 Reminder: Tomorrow is {birthday['name']}'s birthday!"
                    )
        except Exception as e:
            logger.error(f"Error checking upcoming birthdays: {e}")

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_input = update.message.text  # Get the user's input
        chat_id = update.message.chat_id

        # Check if the user wants to save a birthday
        action_save = f'Does the following input suggest an intention to save a birthday: "{user_input}"'
        # Check if the user wants to retrieve birthdays
        action_retrieve = f'Does the following input suggest an intention to retrieve birthday details or show the birthday details: "{user_input}"'

        # Await the checkCondition method
        condition_save = await self.checkCondition(action_save) or 'save' in user_input.lower()
        condition_retrieve = await self.checkCondition(action_retrieve) or 'show' in user_input.lower()

        if condition_save:
            # Parse the user's input using Gemini
            name, birthdate = await self.parse_birthday_input(user_input)

            if not name or not birthdate:
                await update.message.reply_text("Sorry, I couldn't understand your input. Please try again.")
                return

            # Save the birthday to the JSON file
            if await self.save_birthday(name, birthdate, chat_id):
                await update.message.reply_text(f"🎉 Birthday saved for {name} on {birthdate}.")
            else:
                await update.message.reply_text("Failed to save the birthday. Please try again.")

        elif condition_retrieve:
            # Retrieve all birthdays and display them as a table
            table = await self.get_birthdays(chat_id)
            await update.message.reply_text(table)

        else:
            await update.message.reply_text("Sorry, I couldn't understand your request. Please try again.")


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
        elif name == "birthday":
            return BirthdayFunctionality()
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
    birthday_func = FunctionalityFactory.create_functionality("birthday")

    # Message handler to decide which functionality to execute
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Access the job queue from the application instance
    application = bot._instance.application
    job_queue = application.job_queue

    # Schedule the birthday reminder task
    job_queue.run_repeating(
        birthday_func.check_upcoming_birthdays,
        interval=86400,  # Check every 24 hours
        first=10  # Start after 10 seconds
    )

    # Run the bot
    bot.run()


if __name__ == "__main__":
    main()
