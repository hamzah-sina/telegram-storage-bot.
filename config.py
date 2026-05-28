import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token من BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Telegram ID الخاص بك (الأدمن الأول)
# ستُضاف هذه القيمة تلقائياً في قاعدة البيانات عند أول تشغيل
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
