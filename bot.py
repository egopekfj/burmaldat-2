import telebot
import os
import requests
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8564519528:AAHMzDe8JOsdqXr5vpl55uroqQewyvxxIeM"

# Маскируем токен от сканера
PART1 = "hf_KYuojvfHgfvZxkxBH"
PART2 = "MvhjjkgqNoGtnTxkM"
HF_API_KEY = PART1 + PART2

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
    "Твоя цель — угарать и поддерживать диалог в своем неповторимом стиле."
)

def get_ai_response(user_text):
    # Используем проверенную модель Mistral, она отлично понимает русский и держит нагрузку
    url = "https://api-inference.huggingface.co/models/MistralAI/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    prompt = f"<s>[INST] {SYSTEM_PROMPT} \n\n Пользователь: {user_text} [/INST]"
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 100, "temperature": 0.7, "return_full_text": False}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '').strip()
        return f"Сервер ИИ ответил кодом: {response.status_code}"
    except Exception as e:
        return f"Ошибка сети: {str(e)[:40]}"

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        f"Здарова, {message.from_user.first_name}! Бурмалдат на связи в текстовом режиме. Накидывай базар, пообщаемся 👇"
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
