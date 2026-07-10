import os
import random
import requests
from threading import Thread
from flask import Flask
from telebot import TeleBot, types

# Микро-сервер для удержания Render в онлайне
app = Flask('')

@app.route('/')
def home():
    return "Бот работает без цензуры и звездочек!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Достаем токены из настроек Render
API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

bot = TeleBot(API_TOKEN)

# Новый промпт: убрали гопников, оставили только чистый жесткий мат без звездочек
SYSTEM_PROMPT = (
    "Ты — максимально дикий, угарный и неадекватный собеседник. "
    "Ты общаешься с кучей жесткого мата и ругательств для связки слов. "
    "Цензура полностью отключена, тебе МОЖНО И НУЖНО материться на всю катушку. "
    "СТРОГОЕ ПРАВИЛО: Пиши все матерные слова ЦЕЛИКОМ БУКВАМИ. "
    "Никогда не заменяй буквы в матах на звездочки (никаких ***, б**дь, х#й). Пиши слова открыто! "
    "НЕ используй символы звезд '**' для выделения текста. Пиши обычным, чистым текстом без разметки. "
    "Отвечай угарно, жестко, средними по длине сообщениями на русском языке."
)

context_memory = {}

def get_ai_response(chat_id, user_text, special_mode=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/burmaldat", 
        "X-Title": "Burmaldat Bot"
    }
    
    if chat_id not in context_memory:
        context_memory[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        
    if special_mode == "quote":
        prompt_text = "Выдай какую-нибудь максимально дикую, угарную и матерную фразу или мысль. Без звездочек."
    elif special_mode == "joke":
        prompt_text = "Расскажи один очень смешной, пошлый или просто жесткий анекдот с кучей мата. Без звездочек."
    else:
        prompt_text = user_text

    if not special_mode:
        context_memory[chat_id].append({"role": "user", "content": prompt_text})
    
    if len(context_memory[chat_id]) > 7:
        context_memory[chat_id] = [context_memory[chat_id][0]] + context_memory[chat_id][-6:]

    messages_to_send = context_memory[chat_id] if not special_mode else [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text}
    ]

    models_to_try = [
        "deepseek/deepseek-chat",
        "microsoft/phi-3-medium-128k-instruct:free",
        "meta-llama/llama-3-8b-instruct:free"
    ]
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages_to_send,
            "max_tokens": 500
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                ai_answer = response.json()['choices'][0]['message']['content'].strip()
                if not special_mode:
                    context_memory[chat_id].append({"role": "assistant", "content": ai_answer})
                return ai_answer
        except Exception:
            continue
            
    return "Сука, сервера опять легли от твоего бреда! Напиши еще раз чуть позже."

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_quote = types.KeyboardButton("🔥 Выдать базу")
    btn_joke = types.KeyboardButton("🍺 Травнуть анекдот")
    markup.add(btn_quote, btn_joke)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "Здорова! Я твой личный бот-матерщинник. Пиши любой бред или тыкай кнопки внизу, ща устроим угар без цензуры! 😈"
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    user_text = message.text
    
    if user_text == "🔥 Выдать базу":
        bot.send_chat_action(chat_id, 'typing')
        answer = get_ai_response(chat_id, user_text, special_mode="quote")
        bot.send_message(chat_id, answer, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif user_text == "🍺 Травнуть анекдот":
        bot.send_chat_action(chat_id, 'typing')
        answer = get_ai_response(chat_id, user_text, special_mode="joke")
        bot.send_message(chat_id, answer, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    else:
        bot.send_chat_action(chat_id, 'typing')
        answer = get_ai_response(chat_id, user_text)
        bot.send_message(chat_id, answer, reply_markup=get_main_keyboard(), parse_mode='Markdown')

if __name__ == '__main__':
    server_thread = Thread(target=run_web_server)
    server_thread.start()
    bot.infinity_polling()
