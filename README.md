# Flashy
# Flashy AI Assistant (Powered by Ollama & DDG)

A smart, privacy-focused, and context-aware **Telegram AI Bot** built using Python, local LLMs via **Ollama**, and **DuckDuckGo Web Search** for real-time news updates. Designed for seamless deployment on **Render** with 24/7 uptime support.

---

## ✨ Features

- 💬 **Conversational AI:** Fast and natural dialogue powered by local `llama3.2` model.
- 🌐 **Real-Time Web Search:** Automatically fetches live news, current affairs, and trends using DuckDuckGo.
- 🧠 **Context Memory:** Maintains recent chat history for coherent multi-turn conversations.
- 🔒 **Secure Configuration:** Uses environment variables to protect sensitive credentials like `BOT_TOKEN`.
- 🚀 **Render 24/7 Ready:** Embedded Flask web server handles port binding and prevents deployment crashes.

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Bot Framework:** `pyTelegramBotAPI` (Telebot)
- **AI / LLM Engine:** [Ollama](https://ollama.com/) (`llama3.2`)
- **Web Search API:** `duckduckgo_search`
- **Web Server:** Flask (for Render health checks)

---

## 📦 Project Structure

```text
├── main.py             # Main application logic & bot handlers
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
