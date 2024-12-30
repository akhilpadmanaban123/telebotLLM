import logging
import calendar
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from functionalities.base import Functionality
from utils.firebase import get_firestore_client
from utils.config import gemini_model
import tabulate

logger = logging.getLogger(__name__)


class BirthdayFunctionality(Functionality):
    def __init__(self):
        # Initialize Firestore client
        self.db = get_firestore_client()
        self.birthdays = self._load_birthdays()

    def _load_birthdays(self):
        """
        Load birthdays from Firestore.
        """
        birthdays = []
        try:
            firestore_birthdays = self.db.collection("birthdays").stream()
            for doc in firestore_birthdays:
                birthdays.append(doc.to_dict())
        except Exception as e:
            logger.error(f"Error loading birthdays from Firestore: {e}")
        return birthdays

    async def invoke_gemini(self, prompt):
        """
        Send a prompt to the Gemini API and return the response.
        """
        try:
            response = gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error invoking Gemini: {e}")
            return None

    async def checkCondition(self, action):
        """
        Check if the user input suggests a specific action using Gemini.
        """
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
            response = await self.invoke_gemini(prompt)  # Await the response
            if response is None:
                return False

            response_text = response.strip().lower()

            # Debugging: Log the response from Gemini
            logger.info(f"Gemini response for action '{action}': {response_text}")

            # Return True if the response is 'true', otherwise False
            return response_text == 'true'
        except Exception as e:
            logger.error(f"Error checking condition: {e}")
            return False

    async def parse_birthday_input(self, user_input):
        """
        Use Gemini API to extract name and birthdate from the user's input.
        """
        try:
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
            response = await self.invoke_gemini(prompt)
            if response is None:
                return None, None

            # Extract the JSON part from the response
            start_index = response.find("{")
            end_index = response.rfind("}") + 1

            if start_index == -1 or end_index == -1:
                logger.error("No JSON object found in the response.")
                return None, None

            json_str = response[start_index:end_index]

            # Parse the JSON response
            import json  # Import json module
            birthday_data = json.loads(json_str)  # Parse JSON string into a dictionary

            # Extract name and birthdate
            name = birthday_data.get("name", "")
            birthdate = birthday_data.get("birthdate", "")

            if birthdate:
                try:
                    year, month, day = birthdate.split("-")
                    month_number = int(month)
                    month_name = calendar.month_name[month_number]
                    formatted_birthdate = f"{day}-{month_name}-{year}"
                    return name, formatted_birthdate
                except (IndexError, ValueError) as e:
                    logger.error(f"Error formatting birthdate: {e}")
                    return None, None
        except Exception as e:
            logger.error(f"Error parsing birthday input: {e}")
            return None, None

    async def save_birthday(self, name, birthdate, chat_id):
        """
        Save the birthday to Firestore.
        """
        try:
            self.db.collection("birthdays").add({
                "name": name,
                "birthdate": birthdate,
                "chat_id": chat_id
            })
            # Reload birthdays after saving
            self.birthdays = self._load_birthdays()
            return True
        except Exception as e:
            logger.error(f"Error saving birthday to Firestore: {e}")
            return False

    async def get_birthdays(self, chat_id):
        """
        Retrieve all birthdays from Firestore and display them as a visually appealing table.
        """
        try:
            if not self.birthdays:
                return "🎉 No birthdays found."
            print(self.birthdays)
            # Format the birthdays as a table
            table = tabulate.tabulate(
                [(b["name"], b["birthdate"]) for b in self.birthdays],
                headers=["🎈 Name", "📅 Birthdate"],
                tablefmt="fancy_grid"
            )

            # Add a birthday-themed image URL
            image_url = "https://giphy.com/gifs/MickeyMouse-fun-excited-disney-Im6d35ebkCIiGzonjI"

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
        user_input = update.message.text
        chat_id = update.message.chat_id

        # Check if the user wants to save a birthday
        action_save = f'Does the following input suggest an intention to save a birthday: "{user_input}"'
        # Check if the user wants to retrieve birthdays
        action_retrieve = f'Does the following input suggest an intention to retrieve birthday details or show the birthday details: "{user_input}"'

        # Await the checkCondition method
        condition_save = await self.checkCondition(action_save) and 'save' in user_input.lower()
        condition_retrieve = await self.checkCondition(action_retrieve) and 'show' in user_input.lower()

        if condition_save:
            # Parse the user's input using Gemini
            name, birthdate = await self.parse_birthday_input(user_input)

            if not name or not birthdate:
                await update.message.reply_text("Sorry, I couldn't understand your input. Please try again.")
                return

            # Save the birthday to Firestore
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
