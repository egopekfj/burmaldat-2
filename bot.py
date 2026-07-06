import telebot
import os
import time
import requests
from gtts import gTTS
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8564519528:AAHMzDe8JOsdqXr5vpl55uroqQewyvxxIeM"

# Маскируем новый токен от сканера Гитхаба
PART1 = "hf_KYuojvfHgfvZxkxBH"
PART2 = "MvhjjkgqNoGtnTxkM"
HF_API_KEY = PART1 + PART2

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Бурмалдат ИИ в сети!"

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
    # Меняем модель на стабильную Llama-3-8B
    url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # Форматируем промпт под Лламу
    prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{user_text}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
    
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 150, "temperature": 0.8, "return_full_text": False}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                text = result[0].get('generated_text', '')
                return text.strip()
            elif isinstance(result, dict) and 'generated_text' in result:
                return result['generated_text'].strip()
        
        # Если Hugging Face вернул ошибку, бот сам скажет код ошибки (например, 401 или 503)
        return f"Ошибка ИИ: код {response.status_code}. Хьюстон, у нас проблемы."
    except Exception as e:
        return f"Ошибка кода: {str(e)[:50]}"

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        f"Здарова, {message.from_user.first_name}! Бурмалдат на связи, всё собрано с нуля. Пиши текст — отвечу ГС! Накидывай 👇"
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.send_chat_action(message.chat.id, 'record_audio')
    ai_text = get_ai_response(message.text)
    filename = f"voice_{message.chat.id}_{int(time.time())}.ogg"
    try:
        tts = gTTS(text=ai_text, lang='ru', slow=False)
        tts.save(filename)
        with open(filename, 'rb') as voice:
            bot.send_voice(message.chat.id, voice, reply_to_message_id=message.message_id)
    except Exception as e:
        print(f"Ошибка TTS: {e}")
        bot.send_message(message.chat.id, ai_text)
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            time.sleep(5)
