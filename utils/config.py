import google.generativeai as genai

# Replace with your API keys
TELEGRAM_TOKEN = "tele tokennnnn7551480728:AAHXUv-sSrkjluC-Ehubaj1OjUevLRYUbzktokennntelegramknhn"
GEMINI_API_KEY = "geminitokennnnAIzaSyBulnqflbB3SRzg4bR-wnG648jVACQGJ2ggeminii"
BIRTHDAYS_FILE = "Birthdays.json"
FIREBASE_SERVICE_ACCOUNT_KEY = "D:/My Works/TelegramBot/telegrambotllm-firebase-adminsdk-6lsyf-b77d01b0b7.json"

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')
