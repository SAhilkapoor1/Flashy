import os
import sys
import re
from threading import Thread
from duckduckgo_search import DDGS
from flask import Flask
from groq import Groq
import telebot

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
# ⭐ STICKER DATABASE 
# (Yahan apne sticker packs se IDs nikal kar paste karein)
# ==========================================
STICKER_MAP = {
    "laugh": "YAHAN_LAUGH_WALA_ID_DAALEIN", 
    "love": "YAHAN_LOVE_WALA_ID_DAALEIN",
    "sad": "YAHAN_SAD_WALA_ID_DAALEIN",
    "gaali": "YAHAN_GAALI_WALA_ID_DAALEIN",  
    "nsfw": "YAHAN_NSFW_WALA_ID_DAALEIN"     
}

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

SEARCH_KEYWORDS = ["news", "aaj", "khabar", "latest", "current", "today", "update", "kya hua"]

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

# 🛠️ STICKER PACK ID FINDER COMMAND (/getpack PackName)
@bot.message_handler(commands=['getpack'])
def get_sticker_pack(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Bhai pack ka naam bhi likho! Jaise: `/getpack AnimalsAnimation`", parse_mode="Markdown")
            return
        
        pack_name = args[1]
        bot.send_chat_action(message.chat.id, "typing")
        
        sticker_set = bot.get_sticker_set(pack_name)
        response_text = f"📦 **Pack Name:** `{sticker_set.name}`\nTotal Stickers: {len(sticker_set.stickers)}\n\n"
        
        for i, sticker in enumerate(sticker_set.stickers[:10]):
            response_text += f"{i+1}. `{sticker.file_id}`\n\n"
            
        bot.reply_to(message, response_text, parse_motion="Markdown" if hasattr(bot, 'Markdown') else "Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error aa gaya bhai: `{e}`", parse_mode="Markdown")

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

    needs_search = any(keyword in user_text.lower() for keyword in SEARCH_KEYWORDS)
    prompt_to_send = user_text

    if needs_search:
        bot.send_chat_action(user_id, "typing")
        search_data = search_duckduckgo(user_text)
        prompt_to_send = (
            f"User Question: {user_text}\n\n"
            f"[Internet Search Data]:\n{search_data}\n\n"
            f"Instruction: Search data ka use karke ek cool aur friendly Hinglish answer do."
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
        raw_reply = response.choices[0].message.content

        sticker_match = re.search(r'\[STICKER:\s*([a-zA-Z]+)\]', raw_reply)
        sticker_to_send = None

        if sticker_match:
            emotion = sticker_match.group(1).lower()
            if emotion in STICKER_MAP and not STICKER_MAP[emotion].startswith("YAHAN_"): 
                sticker_to_send = STICKER_MAP[emotion]
            clean_reply = re.sub(r'\[STICKER:\s*[a-zA-Z]+\]', '', raw_reply).strip()
        else:
            clean_reply = raw_reply

        user_sessions[user_id].append({"role": "assistant", "content": clean_reply})
        
        if clean_reply:
            bot.reply_to(message, clean_reply)
        if sticker_to_send:
            bot.send_sticker(user_id, sticker_to_send)

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
