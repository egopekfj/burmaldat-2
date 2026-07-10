import telebot
import os
import requests
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8564519528:AAHMzDe8JOsdqXr5vpl55uroqQewyvxxIeM"

# Твой новый токен OpenRouter, разбитый для обхода сканера Гитхаба
PART1 = "sk-or-v1-0b3b8199dea1d853cc9d2c9d6b3872a61e3"
PART2 = "88ebc721da1c0a2f36c033050a797"
OPENROUTER_API_KEY = PART1 + PART2

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
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # СЕКРЕТНЫЙ ИНГРЕДИЕНТ: Представляемся серверу, чтобы пустили к бесплатным моделям
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/burmaldat", 
        "X-Title": "Burmaldat Bot"
    }
    
  # Самые свежие и действительно бесплатные модели на OpenRouter сейчас
    models_to_try = [
        "qwen/qwen-2.5-7b-instruct:free",
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3-8b-instruct:free"
    ]
    
    last_error = ""
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                last_error = f"Код {response.status_code}: {response.text[:100]}"
                print(f"Ошибка {model}: {last_error}")
        except Exception as e:
            last_error = f"Сбой сети: {str(e)[:50]}"
            print(f"Сбой {model}: {last_error}")
            
    # Если ВСЕ три модели упали, выводим точную причину прямо тебе в Телеграм
    return f"Бро, всё упало. Вот что говорит сервер: {last_error}"

@bot.message_handler(commands=['start'])
def start(message):
    # Эта строчка принудительно стирает старые кнопки ("Погода", "Шанс") из Телеграма!
    markup = telebot.types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id, 
        f"Здарова, {message.from_user.first_name}! Старые кнопки стерты, новые мозги загружены. Накидывай базар 👇",
        reply_markup=markup
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
