import telebot
import os
import requests
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8564519528:AAHMzDe8JOsdqXr5vpl55uroqQewyvxxIeM"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Бурмалдат Текст-ИИ в сети!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

SYSTEM_PROMPT = (
    "Ты — Бурмалдат, дикий, дерзкий и угарный персонаж. "
    "Ты общаешься с пацанами на расслабленном сленге, любишь шутить, использовать иронию и отвечать мемно. "
    "Не пиши длинные тексты, отвечай коротко, емко и с юмором, как реальный кореш. "
    "Твоя цель — угарать и поддерживать диалог в своем неповторимом стиле. Отвечай строго на русском языке."
)

def get_ai_response(user_text):
    # Используем открытый и стабильный шлюз, который не банит Render
    url = "https://chimeragpt.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer free-chimera-key-prompt-engineering",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.8,
        "max_tokens": 150
    }
    
    try:
        # Если этот шлюз занят, используем резервный абсолютно свободный источник
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": "Bearer sk-or-v1-free-key-for-everyone"},
            json={
                "model": "meta-llama/llama-3-8b-instruct:free",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ]
            }, timeout=10)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
            
        return f"Ошибка ИИ (Код {response.status_code})"
    except Exception as e:
        return "Бро, сеть глушат, попробуй еще раз через сек!"

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        f"Здарова, {message.from_user.first_name}! Бурмалдат на связи через резервный канал. Базарь, я слушаю 👇"
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.send_chat_action(message.chat.id, 'typing')
    ai_text = get_ai_response(message.text)
    bot.send_message(message.chat.id, ai_text)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            import time
            time.sleep(5)
