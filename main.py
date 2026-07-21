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
# Bot is pack ke saare stickers mein se automatic random sticker utha lega!
STICKER_PACK_NAMES = {
    "laugh": "Chikkiku", 
    "love": "honeyflynn_by_fStikBot",
    "sad": "Konsa_Tara_by_fStikBot",
    "gaali": "ShimtPostStimkers",  
    "nsfw": "MeowThree_by_fStikBot"     
}

# Helper function to get a random sticker from a pack
def send_pack_sticker(chat_id, emotion):
    try:
        pack_name = STICKER_PACK_NAMES.get(emotion)
        if not pack_name or pack_name.startswith("YAHAN_"):
            return
        
        # Telegram se sticker set fetch karo
        sticker_set = bot.get_sticker_set(pack_name)
        if sticker_set and sticker_set.stickers:
            # Pack ke saare stickers me se koi ek random sticker chun lo
            random_sticker = random.choice(sticker_set.stickers)
            bot.send_sticker(chat_id, random_sticker.file_id)
    except Exception as e:
        print(f"❌ Sticker pack load karne mein error: {e}")

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
            search_results = list(ddgs.text(query, max_results=3))
            for r in search_results:
                results.append(f"Title: {r['title']}\nSnippet: {r['body']}")
        if results:
            return "\n\n".join(results)
        return "No web results found."
    except:
        return "Search failed."

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
        "5. Empathy: Agar user pareshan hai, mazaak kar raha hai, gaali de raha hai ya 18+ chat kar raha hai, toh uski tone se match karke reply dein. \n"
        "6. 🔴 STICKERS RULE (CRITICAL): Agar situation ke hisaab se koi emotion dikhana ho, ya user gaali/18+ chat kar raha ho toh message ke bilkul AAKHIRI mein yeh tag lagayein: "
        "[STICKER: laugh], [STICKER: love], [STICKER: sad], [STICKER: gaali], ya [STICKER: nsfw]."
    ),
}

SEARCH_KEYWORDS = ["news", "aaj", "khabar", "latest", "current", "today", "update", "kya hua", "weather", "mausam"]

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
    prompt_to_send = user_text

    search_data = ""
    if needs_search:
        bot.send_chat_action(user_id, "typing")
        search_data = search_duckduckgo(user_text)

    # Context inject with Real-time Date, Time & Search Data
    prompt_to_send = (
        f"[Current Real-Time Context]: Date & Time (IST): {current_datetime}\n"
        f"User Question: {user_text}\n\n"
    )
    if needs_search and search_data:
        prompt_to_send += f"[Internet Live Browsing Data]:\n{search_data}\n\n"
    
    prompt_to_send += "Instruction: Real-time date/time aur search data ka use karke ek cool aur friendly Hinglish answer do."

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
        raw_reply = response.choices[0].message.content

        sticker_match = re.search(r'\[STICKER:\s*([a-zA-Z]+)\]', raw_reply)
        emotion_to_send = None

        if sticker_match:
            emotion_to_send = sticker_match.group(1).lower()
            clean_reply = re.sub(r'\[STICKER:\s*[a-zA-Z]+\]', '', raw_reply).strip()
        else:
            clean_reply = raw_reply

        user_sessions[user_id].append({"role": "assistant", "content": clean_reply})
        
        if clean_reply:
            bot.reply_to(message, clean_reply)
        
        if emotion_to_send and emotion_to_send in STICKER_PACK_NAMES:
            send_pack_sticker(user_id, emotion_to_send)

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
