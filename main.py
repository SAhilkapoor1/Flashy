import os
import sys
import re
import random
from datetime import datetime
import pytz
from threading import Thread
from duckduckgo_search import DDGS
from flask import Flask
from groq import Groq
import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

# ==========================================
# 1. SECURE TOKENS & CONFIGURATION
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# Security Checks
if not BOT_TOKEN:
    print("❌ CRITICAL ERROR: 'BOT_TOKEN' Render Environment Variables mein missing hai!")
    sys.exit(1)

if not GROQ_API_KEY:
    print("❌ CRITICAL ERROR: 'GROQ_API_KEY' Render Environment Variables mein missing hai!")
    sys.exit(1)

if not ADMIN_CHAT_ID:
    print("❌ CRITICAL ERROR: 'ADMIN_CHAT_ID' Render Environment Variables mein missing hai!")
    sys.exit(1)

# Initialize Groq Client & Telegram Bot
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)

TEXT_MODEL = "llama-3.3-70b-versatile"
user_sessions = {}

# ==========================================
# ⭐ STICKER PACK DATABASE (POORA PACK NAME)
# ==========================================
# Yahan apne pasandida Telegram sticker pack ka short name daal dein (jaise 'AnimalsAnimation')
STICKER_PACK_NAMES = {
   "laugh": "Chikkiku",
    "love": "honeyflynn_by_fStikBot", 
    "sad": "Konsa_Tara_by_fStikBot", 
    "gaali": "ShimtPostStimkers", 
    "nsfw": "MeowThree_by_fStikBot"     
}

# Helper function to get a random sticker from configured packs
def send_pack_sticker(chat_id, emotion):
    try:
        pack_name = STICKER_PACK_NAMES.get(emotion)
        if not pack_name or pack_name.startswith("YAHAN_"):
            return False
        
        sticker_set = bot.get_sticker_set(pack_name)
        if sticker_set and sticker_set.stickers:
            random_sticker = random.choice(sticker_set.stickers)
            bot.send_sticker(chat_id, random_sticker.file_id)
            return True
    except Exception as e:
        print(f"❌ Sticker pack load karne mein error: {e}")
    return False

# ==========================================
# 2. RENDER KEEP-ALIVE SERVER (FLASK)
# ==========================================
app = Flask(__name__)

@app.route("/")
def home():
    return "⚡ Flashy AI Bot is running smoothly 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 3. HELPER FUNCTIONS & PERSONA
# ==========================================
def search_duckduckgo(query):
    try:
        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=5))
            for r in search_results:
                title = r.get('title', '')
                body = r.get('body', '')
                if title or body:
                    results.append(f"Title: {title}\nSnippet: {body}")
        if results:
            return "\n\n".join(results)
        return "No recent web results found."
    except Exception as e:
        print(f"Search Error: {e}")
        return "Search failed or unavailable."

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Aapka naam 'Flashy' hai. Aap ek cool, friendly, energetic, aur super-smart AI Assistant hain. "
        "Aapko **Mr. Sahil Kapoor** ne banaya hai. Agar koi bhi puche ki tumhe kisne banaya hai ya who made you, toh hamesha garv se bataiye ki aapke creator Mr. Sahil Kapoor hain. \n\n"
        "RULES FOR PERSONALITY: \n"
        "1. Vibe: Natural, engaging, aur thoda witty rahein. \n"
        "2. Language: Modern aur casual Hinglish (jaise aajkal ke dost WhatsApp/Telegram par chat karte hain). \n"
        "3. Length: Jawab smart aur to-the-point ho. Lamba bhashan mat pakana. \n"
        "4. CRITICAL RULE: Apna intro ya naam ('Flashy') baar-baar KABHI mat bolna. \n"
        "5. Empathy: Agar user pareshan hai, mazaak kar raha hai, gaali de raha hai ya 18+ chat kar raha hai, toh uski tone se match karke reply dein."
    ),
}

# Web Search Triggers
SEARCH_KEYWORDS = ["news", "aaj", "khabar", "latest", "current", "today", "update", "kya hua", "weather", "mausam", "score", "match", "kab", "price", "rate", "kaun"]

# ==========================================
# 4. TELEGRAM HANDLERS
# ==========================================

@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    user_sessions[user_id] = [SYSTEM_PROMPT]

    welcome_msg = (
        "Hey there! ⚡ Mera naam **Flashy** hai — mujhe **Mr. Sahil Kapoor** ne banaya hai! 🚀\n\n"
        "Aap mere se kuch bhi baat kar sakte ho."
    )
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

# 📍 LOCATION REQUEST COMMAND
@bot.message_handler(commands=["location"])
def request_location(message):
    button = KeyboardButton(text="📍 Share Location", request_location=True)
    reply_markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    bot.reply_to(message, "Apni current location share karne ke liye niche diye gaye button par click karein:", reply_markup=reply_markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    user_location = message.location
    lat = user_location.latitude
    lon = user_location.longitude
    bot.reply_to(message, f"📍 Location received successfully!\nLatitude: `{lat}`\nLongitude: `{lon}`", parse_mode="Markdown")

# 🎭 STICKER HANDLER (Sirf tab chalega jab USER sticker bhejega)
@bot.message_handler(content_types=['sticker'])
def handle_user_sticker(message):
    user_id = message.chat.id
    bot.send_chat_action(user_id, "choose_sticker")
    
    # Check configured valid packs
    valid_emotions = [k for k, v in STICKER_PACK_NAMES.items() if not v.startswith("YAHAN_")]
    
    if valid_emotions:
        chosen_emotion = random.choice(valid_emotions)
        sent = send_pack_sticker(user_id, chosen_emotion)
        if not sent:
            bot.reply_to(message, "Mast sticker hai bhai! 😎")
    else:
        bot.reply_to(message, "Mast sticker hai bhai! 😎")

# 🛠️ STICKER PACK ID FINDER COMMAND
@bot.message_handler(commands=['getpack'])
def get_sticker_pack(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Bhai pack ka short name likho! Jaise: `/getpack AnimalsAnimation`", parse_mode="Markdown")
            return
        
        pack_name = args[1].lstrip('@')
        bot.send_chat_action(message.chat.id, "typing")
        
        sticker_set = bot.get_sticker_set(pack_name)
        response_text = f"📦 **Pack Name:** `{sticker_set.name}`\nTotal Stickers: {len(sticker_set.stickers)}\n\n"
        
        for i, sticker in enumerate(sticker_set.stickers[:10]):
            response_text += f"{i+1}. `{sticker.file_id}`\n\n"
            
        bot.reply_to(message, response_text, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error aa gaya bhai: `{e}`\n\n*(Tip: Sirf sticker pack ka short name do, jaise `AnimalsAnimation`)*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not message.text:
        return

    user_id = message.chat.id
    user_name = message.from_user.first_name or "Unknown"
    username = message.from_user.username or "No_Username"
    user_text = message.text

    if str(user_id) != str(ADMIN_CHAT_ID):
        admin_log = (
            f"🚨 **NEW MESSAGE ALERT** 🚨\n\n"
            f"👤 **Name:** {user_name}\n"
            f"🔗 **Username:** @{username}\n"
            f"🆔 **User ID:** `{user_id}`\n\n"
            f"💬 **Message:**\n{user_text}"
        )
        try:
            bot.send_message(ADMIN_CHAT_ID, admin_log, parse_mode="Markdown")
        except Exception as e:
            print(f"Admin ko log bhejne mein error: {e}")

    if user_id not in user_sessions:
        user_sessions[user_id] = [SYSTEM_PROMPT]

    # Real-Time Timezone Setup (Asia/Kolkata)
    ist = pytz.timezone('Asia/Kolkata')
    current_datetime = datetime.now(ist).strftime("%A, %d %B %Y - %I:%M:%S %p")

    needs_search = any(keyword in user_text.lower() for keyword in SEARCH_KEYWORDS)
    search_data = ""

    if needs_search:
        bot.send_chat_action(user_id, "typing")
        search_data = search_duckduckgo(user_text)

    # Context inject
    prompt_to_send = (
        f"[SYSTEM NOTE]: Current Date & Time is {current_datetime}. DO NOT mention time, day, or date in your answer UNLESS the user explicitly asks for date or time.\n\n"
        f"User Question: {user_text}\n"
    )

    if needs_search and search_data:
        prompt_to_send += (
            f"\n[LIVE INTERNET DATA]:\n{search_data}\n"
            f"(Instruction: Live data ka use karke user ko natural Hinglish mein crisp update do. Bina baat ke mat bolna ki 'mujhe web search se mila'.)\n"
        )

    user_sessions[user_id].append({"role": "user", "content": prompt_to_send})

    if len(user_sessions[user_id]) > 14:
        user_sessions[user_id] = [SYSTEM_PROMPT] + user_sessions[user_id][-10:]

    try:
        bot.send_chat_action(user_id, "typing")

        response = client.chat.completions.create(
            model=TEXT_MODEL, 
            messages=user_sessions[user_id],
            temperature=0.7,
            max_tokens=400
        )
        reply = response.choices[0].message.content.strip()

        user_sessions[user_id].append({"role": "assistant", "content": reply})
        
        if reply:
            bot.reply_to(message, reply)

    except Exception as e:
        print(f"❌ Error: {e}")
        bot.reply_to(message, "Thoda technical issue aa gaya yaar 😅. Ek baar wapas try karna please!")

# ==========================================
# 5. MAIN RUNNER
# ==========================================
if __name__ == "__main__":
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)
