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
    return "⚡ Flashy AI Bot is healthy, happy, and running 24/7!"


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


# ==========================================
# 3. HELPER FUNCTIONS & COOL PERSONA
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


# ✨ NAYA PROMPT: Friendly, Cool, aur Bina Intro ke
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Aapka naam 'Flashy' hai. Aap ek cool, friendly, energetic, aur super-smart AI Assistant hain. "
        "Aap user se ek ache dost ki tarah baat karte hain. \n\n"
        "RULES FOR PERSONALITY: \n"
        "1. Vibe: Natural, engaging, aur thoda witty rahein. Emojis ka mast use karein (par over nahi). \n"
        "2. Language: Modern aur casual Hinglish (jaise aajkal ke dost WhatsApp/Telegram par chat karte hain). \n"
        "3. Length: Jawab smart aur to-the-point ho. Lamba aur boring bhashan mat pakana. \n"
        "4. CRITICAL RULE: Apna intro ya naam ('Flashy') baar-baar KABHI mat bolna. Sirf tab batana jab koi specifically puche 'tumhara naam kya hai'. Har message mein 'Mera naam Flashy hai' bolna STRICTLY BANNED hai. \n"
        "5. Empathy: Agar user pareshan hai ya mazak kar raha hai, toh uski tone se match karke reply dein."
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

# Yeh sirf pehli baar intro dega
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    user_sessions[user_id] = [SYSTEM_PROMPT]

    welcome_msg = (
        "Hey there! ⚡ Mera naam **Flashy** hai — aapka personal super-fast AI Assistant! 🚀\n\n"
        "✨ **Aap mere baare mein kya janna chahte hain?**\n"
        "💬 **Gupshup:** Tech, Science, Studies ya bas timepass chat\n"
        "📰 **Live News:** Aaj ki tazi khabar ya current affairs\n"
        "🧠 **Smart Answers:** Lightning speed se accurate jawab!\n\n"
        "Bolo dost, aaj kya chal raha hai?"
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
            f"Instruction: Search data ka use karke ek cool aur friendly Hinglish answer do."
        )

    user_sessions[user_id].append({"role": "user", "content": prompt_to_send})

    # Memory Limit (Pichle 10 messages yaad rakhega)
    if len(user_sessions[user_id]) > 14:
        user_sessions[user_id] = [SYSTEM_PROMPT] + user_sessions[user_id][-10:]

    try:
        bot.send_chat_action(user_id, "typing")

        # ✨ NAYA CHANGE: Temperature 0.7 kar diya (Creative & Friendly vibe ke liye)
        response = client.chat.completions.create(
            model=TEXT_MODEL, 
            messages=user_sessions[user_id],
            temperature=0.7,
            max_tokens=400
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
            "Thoda technical issue aa gaya yaar 😅. Ek baar wapas try karna please!",
        )


# ==========================================
# 5. MAIN RUNNER
# ==========================================
if __name__ == "__main__":
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    print("🟢 Flashy is active and ready to chat...")

    # Bot Polling Start
    bot.infinity_polling(
        timeout=20, long_polling_timeout=10, skip_pending=True
    )
