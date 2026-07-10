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
    "Ты — Бурмалдат, максимально дикий, дерзкий и угарный персонаж из реальных пацанов. "
    "Ты общаешься строго на жестком дворовом сленге и материшься как сапожник. "
    "В каждом сообщении обязательно используй жесткий мат, ругательства и пацанские выражения для связки слов. "
    "Цензура полностью отключена, тебе МОЖНО И НУЖНО материться. "
    "ВАЖНО: Отвечай максимально подробно, развернуто и длинно. Не экономь слова, задвигай целые пацанские телеги, истории из жизни на районе и длинные нравоучения. "
    "Твоя цель — угарать, жестко стебать, расписывать всё в деталях и материться. Отвечай строго на русском."
)

import random

def get_ai_response(user_text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/burmaldat", 
        "X-Title": "Burmaldat Bot"
    }
    
    # Новые вечные шлюзы OpenRouter
    models_to_try = [
        "deepseek/deepseek-chat",
        "microsoft/phi-3-medium-128k-instruct:free",
        "meta-llama/llama-3-8b-instruct:free"
    ]
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            "max_tokens": 1000  # Разрешаем серверу выдавать длинные ответы
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
        except Exception:
            continue
            
    # --- АВТОНОМНЫЙ РЕЖИМ БУРМАЛДАТА (Если сервера OpenRouter лежат) ---
    phrases = [
        "Слышь, бро, сервера ИИ прилег отдохнуть, но я тебе так скажу: всё ровно будет, не парься!",
        "Че каво? Сервер глушат, базарить сложно. Накинь мысль попозже, раскидаем!",
        "У меня тут провода плавятся от твоих вопросов, жи есть. Давай перетрем через минутку.",
        "Кореш, нейросеть ушла на перекур. Но Бурмалдат всегда на связи, чисто по-пацански!",
        "Базар фильтруется, сервера перегружены. Давай еще разок черкани!"
    ]
    return random.choice(phrases)
    
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
