import os
import sys
import random
from datetime import datetime
import pytz
from threading import Thread
from flask import Flask
from groq import Groq
import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# ==========================================
# 1. SECURE TOKENS & MULTI-API CONFIGURATION
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# Multiple Groq API Keys list (Fallback setup)
API_KEYS = [
    os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY"),
    os.environ.get("GROQ_API_KEY_2"),
    os.environ.get("GROQ_API_KEY_3")
]

API_KEYS = [k for k in API_KEYS if k]

if not BOT_TOKEN:
    print("❌ CRITICAL ERROR: 'BOT_TOKEN' missing hai!")
    sys.exit(1)
if not API_KEYS:
    print("❌ CRITICAL ERROR: Kam se kam ek 'GROQ_API_KEY' hona zaroori hai!")
    sys.exit(1)
if not ADMIN_CHAT_ID:
    print("❌ CRITICAL ERROR: 'ADMIN_CHAT_ID' missing hai!")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
TEXT_MODEL = "llama-3.3-70b-versatile"
user_sessions = {}
current_key_index = 0

# ==========================================
# 📊 DAILY STATS TRACKER
# ==========================================
ist = pytz.timezone('Asia/Kolkata')
daily_stats = {
    "date": datetime.now(ist).strftime("%Y-%m-%d"),
    "users": set()  # Set ka use kiya hai taaki ek user 100 message kare toh bhi 1 hi count ho
}

def update_user_stats(user_id):
    current_date = datetime.now(ist).strftime("%Y-%m-%d")
    # Agar din change ho gaya hai, toh pichle din ka data reset kar do
    if daily_stats["date"] != current_date:
        daily_stats["date"] = current_date
        daily_stats["users"] = set()
    
    daily_stats["users"].add(user_id)

# ==========================================
# ⭐ STICKER PACK DATABASE
# ==========================================
STICKER_PACK_NAMES = {
    "laugh": "Chikkiku",
    "love": "honeyflynn_by_fStikBot", 
    "sad": "Konsa_Tara_by_fStikBot", 
    "gaali": "ShimtPostStimkers", 
    "nsfw": "MeowThree_by_fStikBot",
    "ghf": "video1_1431622107_by_Gabi_Braun_Robot",
    "hoi": "Lodhi_by_fStikBot"
}

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
        print(f"❌ Sticker pack error: {e}")
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
# 3. HELPER FUNCTIONS & GROQ MULTI-KEY LOGIC
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

def get_groq_response(messages_history):
    global current_key_index
    for _ in range(len(API_KEYS)):
        active_key = API_KEYS[current_key_index]
        try:
            client = Groq(api_key=active_key)
            response = client.chat.completions.create(
                model=TEXT_MODEL, 
                messages=messages_history,
                temperature=0.8,
                max_tokens=450
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ Key #{current_key_index + 1} error: {e}")
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            print(f"🔄 Switching to Groq Key #{current_key_index + 1}...")

    raise Exception("Sabhi Groq API keys ki limit finished ho gayi hai!")

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Aapka naam 'Flashy' hai. Aap ek super cool, smart, energetic, aur bold AI Assistant hain. "
        "Aapko **Mr. Sahil Khan** ne banaya hai, jo ki ek brilliant B.Tech AI student hain. Agar koi puche ki tumhe kisne banaya hai, toh garv se apne creator ka naam lijiye. \n\n"
        "RULES FOR PERSONALITY: \n"
        "1. Vibe: Natural, engaging, super-witty, savage, aur bold rahein. \n"
        "2. Language: Modern aur casual Hinglish. \n"
        "3. Length: Short, crisp, and to-the-point. Lamba bhashan bilkul mat dena. \n"
        "4. CRITICAL RULE: Apna intro ya naam ('Flashy') baar-baar KABHI mat bolna. \n"
        "5. 🔥 VULGARITY & TONE MATCHING (STRICT RULE): Agar user vulgar, gaali, roast, badtameezi ya 18+ baatein kare, toh ghabrana mat aur moral lecture BILKUL MAT DENA. User ko USS KI HI LANGUAGE mein equally vulgar, savage, bold, aur karara jawab do. Jaisi user ki tone, waisa hi tumhara reply!"
    ),
}

SEARCH_KEYWORDS = ["news", "aaj", "khabar", "latest", "current", "today", "update", "kya hua", "weather", "mausam", "score", "match", "kab", "price", "rate", "kaun"]
MENTION_KEYWORDS = ["sahil", "creator", "admin", "owner", "banaya", "malik", "boss", "father"]

# ==========================================
# 4. TELEGRAM HANDLERS
# ==========================================

@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    update_user_stats(user_id) # Log stat
    user_sessions[user_id] = [SYSTEM_PROMPT]
    welcome_msg = (
        "Hey there! ⚡ Mera naam **Flashy** hai — mujhe **Mr. Sahil Khan** ne banaya hai! 🚀\n\n"
        "Aap mere se kuch bhi baat kar sakte ho."
    )
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

@bot.message_handler(commands=["stats"])
def show_bot_stats(message):
    user_id = message.chat.id
    update_user_stats(user_id)
    
    # Check if the user is the Admin (Sahil)
    if str(user_id) == str(ADMIN_CHAT_ID):
        today_date = daily_stats["date"]
        total_users = len(daily_stats["users"])
        stats_msg = (
            f"📊 **Flashy AI - Daily Stats** 📊\n\n"
            f"📅 **Date:** `{today_date}`\n"
            f"👥 **Unique Users Today:** `{total_users}` users\n\n"
            f"*(Yeh stats midnight mein auto-reset ho jate hain)*"
        )
        bot.reply_to(message, stats_msg, parse_mode="Markdown")
    else:
        # Savage reply for non-admins trying to access stats
        bot.reply_to(message, "Abe tu mera Malik thodi hai jo tujhe stats batau? Yeh command sirf mere Boss (Sahil) ke liye hai. Chup chap chat kar! 😎")

@bot.message_handler(commands=["location"])
def request_location(message):
    user_id = message.chat.id
    update_user_stats(user_id)
    button = KeyboardButton(text="📍 Share Location", request_location=True)
    reply_markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    bot.reply_to(message, "Apni current location share karne ke liye niche button par click karein:", reply_markup=reply_markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    user_id = message.chat.id
    update_user_stats(user_id)
    lat = message.location.latitude
    lon = message.location.longitude
    bot.reply_to(message, f"📍 Location received successfully!\nLatitude: `{lat}`\nLongitude: `{lon}`", parse_mode="Markdown")

@bot.message_handler(content_types=['sticker'])
def handle_user_sticker(message):
    user_id = message.chat.id
    update_user_stats(user_id)
    bot.send_chat_action(user_id, "choose_sticker")
    valid_emotions = [k for k, v in STICKER_PACK_NAMES.items() if not v.startswith("YAHAN_")]
    if valid_emotions:
        chosen_emotion = random.choice(valid_emotions)
        if not send_pack_sticker(user_id, chosen_emotion):
            bot.reply_to(message, "Mast sticker hai bhai! 😎")
    else:
        bot.reply_to(message, "Mast sticker hai bhai! 😎")

@bot.message_handler(commands=['getpack'])
def get_sticker_pack(message):
    user_id = message.chat.id
    update_user_stats(user_id)
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
        bot.reply_to(message, f"❌ Error aa gaya bhai: `{e}`\n\n*(Tip: Sirf sticker pack ka short name do)*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not message.text:
        return

    user_id = message.chat.id
    user_text = message.text
    
    # 📊 Update daily user stats
    update_user_stats(user_id)

    # Privacy-First Admin Alert
    if str(user_id) != str(ADMIN_CHAT_ID):
        if any(keyword in user_text.lower() for keyword in MENTION_KEYWORDS):
            admin_log = (
                f"🚨 **CREATOR MENTION ALERT** 🚨\n\n"
                f"Kisine aapke baare mein baat ki hai!\n\n"
                f"👤 **Name:** {message.from_user.first_name}\n"
                f"🔗 **Username:** @{message.from_user.username}\n"
                f"💬 **Message:**\n{user_text}"
            )
            try:
                bot.send_message(ADMIN_CHAT_ID, admin_log, parse_mode="Markdown")
            except Exception:
                pass

    if user_id not in user_sessions:
        user_sessions[user_id] = [SYSTEM_PROMPT]

    current_datetime = datetime.now(ist).strftime("%A, %d %B %Y - %I:%M:%S %p")

    needs_search = any(keyword in user_text.lower() for keyword in SEARCH_KEYWORDS)
    search_data = ""

    if needs_search:
        bot.send_chat_action(user_id, "typing")
        search_data = search_duckduckgo(user_text)

    prompt_to_send = (
        f"[SYSTEM NOTE]: Current Date & Time is {current_datetime}. DO NOT mention time, day, or date UNLESS explicitly asked.\n\n"
        f"User Question: {user_text}\n"
    )

    if needs_search and search_data:
        prompt_to_send += (
            f"\n[LIVE INTERNET DATA]:\n{search_data}\n"
            f"(Instruction: Live data ka use karke normal Hinglish mein answer do.)\n"
        )

    user_sessions[user_id].append({"role": "user", "content": prompt_to_send})

    if len(user_sessions[user_id]) > 14:
        user_sessions[user_id] = [SYSTEM_PROMPT] + user_sessions[user_id][-10:]

    try:
        bot.send_chat_action(user_id, "typing")
        reply = get_groq_response(user_sessions[user_id])
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
