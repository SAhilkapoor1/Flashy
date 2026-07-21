import os
import sys
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

# Security Checks
if not BOT_TOKEN:
    print("❌ CRITICAL ERROR: 'BOT_TOKEN' Render Environment Variables mein missing hai!")
    sys.exit(1)

if not GROQ_API_KEY:
    print("❌ CRITICAL ERROR: 'GROQ_API_KEY' Render Environment Variables mein missing hai!")
    sys.exit(1)

# Initialize Groq Client & Telegram Bot
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)

TEXT_MODEL = "llama-3.3-70b-versatile"  # Groq ka fast & free model
user_sessions = {}


# ==========================================
# 2. RENDER KEEP-ALIVE SERVER (FLASK)
# ==========================================
app = Flask(__name__)


@app.route("/")
def home():
    return "⚡ Flashy AI Bot (Groq Engine) is healthy and running 24/7!"


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


# ==========================================
# 3. HELPER FUNCTIONS & STRICT PERSONA
# ==========================================
def search_duckduckgo(query):
    """DuckDuckGo se Web Search karne ke liye"""
    print(f"\n🌐 [Web Search]: Searching for '{query}'...")
    try:
        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=3))
            for r in search_results:
                results.append(f"Title: {r['title']}\nSnippet: {r['body']}")

        if results:
            return "\n\n".join(results)
        return "No web results found."
    except Exception as e:
        print(f"❌ [Search Error]: {e}")
        return "Search failed."


# Bot ka ekdum strict behavior rule (No Intro, No Faltu Bhashan)
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Aap ek fast aur smart AI Assistant hain. "
        "CRITICAL INSTRUCTIONS: "
        "1. Jawab bilkul TO THE POINT aur chota dein. Sirf sawal ka exact answer dein. "
        "2. KABHI BHI apna introduction na dein. Apna naam KABHI BHI use mat karein. (Introduction is STRICTLY BANNED). "
        "3. Faltu ke conversational fillers (jaise 'Hello', 'Main samajhta hoon', 'Yaar', 'Mera naam Flashy hai') bilkul use na karein. "
        "4. Language: Natural aur direct Hinglish. Seedhe mudde ki baat karein."
    ),
}

SEARCH_KEYWORDS = [
    "news",
    "aaj",
    "khabar",
    "latest",
    "current",
    "today",
    "update",
    "kya hua",
]


# ==========================================
# 4. TELEGRAM HANDLERS
# ==========================================

# Yeh sirf start hone par intro dega
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    user_sessions[user_id] = [SYSTEM_PROMPT]

    welcome_msg = (
        "Hey there! ⚡ Mera naam **Flashy** hai — aapka personal super-fast AI Assistant! 🚀\n\n"
        "✨ **Main aapki kya help kar sakta hoon?**\n"
        "💬 **Instant Chat:** Tech, Science, Studies ya Koi bhi topic par baat karein\n"
        "📰 **Live News Updates:** Aaj ki top news aur current affairs puchen\n"
        "🧠 **Smart Answers:** Fast aur accurate answers lightning speed se!\n\n"
        "Bataiye, aaj kis topic par baat karni hai?"
    )
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")


# Main Chat Handler
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_text = message.text
    print(f"\n💬 [User {user_id}]: {user_text}")

    if user_id not in user_sessions:
        user_sessions[user_id] = [SYSTEM_PROMPT]

    needs_search = any(
        keyword in user_text.lower() for keyword in SEARCH_KEYWORDS
    )
    prompt_to_send = user_text

    if needs_search:
        bot.send_chat_action(user_id, "typing")
        search_data = search_duckduckgo(user_text)
        prompt_to_send = (
            f"User Question: {user_text}\n\n"
            f"[Internet Search Data]:\n{search_data}\n\n"
            f"Instruction: Search data ke basis par sirf kaam ki baat ka direct Hinglish answer dein."
        )

    user_sessions[user_id].append({"role": "user", "content": prompt_to_send})

    # Memory Limit (Pichle 10 messages yaad rakhega)
    if len(user_sessions[user_id]) > 14:
        user_sessions[user_id] = [SYSTEM_PROMPT] + user_sessions[user_id][-10:]

    try:
        bot.send_chat_action(user_id, "typing")

        # Groq Cloud API Call (Temperature = 0.3 kiya hai taaki point-to-point baat kare)
        response = client.chat.completions.create(
            model=TEXT_MODEL, 
            messages=user_sessions[user_id],
            temperature=0.3,
            max_tokens=300
        )
        bot_reply = response.choices[0].message.content

        user_sessions[user_id].append(
            {"role": "assistant", "content": bot_reply}
        )
        bot.reply_to(message, bot_reply)
        print("✅ [Flashy Reply]: Sent successfully via Groq.")

    except Exception as e:
        print(f"❌ [Processing Error]: {e}")
        bot.reply_to(
            message,
            "Thoda technical issue aa raha hai. Please dubara try karein.",
        )


# ==========================================
# 5. MAIN RUNNER
# ==========================================
if __name__ == "__main__":
    # Flask ko background mein chalana zaroori hai Render ke liye
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    print("🟢 Flashy is listening for Telegram messages...")

    # Bot Polling Start
    bot.infinity_polling(
        timeout=20, long_polling_timeout=10, skip_pending=True
    )
