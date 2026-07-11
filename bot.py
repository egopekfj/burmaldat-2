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
    return "Разнообразный черный оракул в сети!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Достаем токены из настроек Render
API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

bot = TeleBot(API_TOKEN)

# Список карт
TIKTOK_CARDS = [
    "Сова со скакалкой",
    "Конь с удочкой",
    "Тигр фокусник",
    "Собака с клюшкой",
    "Жираф с пузыриками",
    "Енот на машине",
    "Балерина свинья",
    "Медведь на скейтборде",
    "Пингвин с воздушным змеем",
    "Лемур",
    "Птица художник",
    "Дельфин боксер",
    "Белка плавает"
]

# Системный промпт (убрали цикличные триггеры, добавили требование разнообразия)
SYSTEM_PROMPT = (
    "Ты — максимально дикий, угарный и неадекватный собеседник с чернейшим чувством юмора. "
    "Ты общаешься с кучей жесткого мата. Цензура полностью отключена. "
    "Шути самый жесткий черный юмор про семью, родственников, внезапные болезни, маразм и абсурдные ситуации. "
    "СТРОГОЕ ПРАВИЛО: Пиши все матерные слова ЦЕЛИКОМ БУКВАМИ. Никаких звездочек. "
    "КАЖДЫЙ раз придумывай абсолютно НОВУЮ, уникальную шизофреническую ситуацию. "
    "Не повторяй одни и те же темы (про дурку, болото и т.д.). Будь максимально непредсказуемым! "
    "ОТВЕЧАЙ СРЕДНЕ (примерно 4-7 предложений), выдавай концентрированный и проработанный трэш. "
    "НЕ пиши текст КАПСОМ. НЕ используй символы звезд '**'. Пиши чистым текстом."
)

context_memory = {}

def get_ai_response(chat_id, user_text, special_mode=None, chosen_card=None, user_number=None):
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
        prompt_text = "Выдай максимально дикую, матерную и чернушную мысль про жизнь или родственников."
    elif special_mode == "joke":
        prompt_text = "Расскажи один смешной и максимально черный анекдот с кучей мата про болезни или безумную родню."
    elif special_mode == "oracle_card":
        prompt_text = (
            f"Пользователь выбрал число {user_number}. Твоя главная задача — обыграть карту '{chosen_card}' из мемных гаданий ТикТока. "
            f"НЕ ПИШИ КАПСОМ. Выдай жесткое, упоротое и матерное предсказание будущего по этой карте. "
            f"Используй черный юмор: приплети туда семью пользователя, придумай уникальный, абсурдный сюжет "
            f"про их родственников, внезапные странные болезни, нелепые бытовые катастрофы или маразм. "
            f"ВАЖНО: Придумай совершенно новый бред, забудь про дурку и больницы, если писал про них в прошлый раз! "
            f"Смешай этот сюр с отборным матом. Никаких звездочек в тексте!"
        )
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
            "max_tokens": 400  # Достаточный объем для развернутого, но не бесконечного ответа
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
    btn_oracle = types.KeyboardButton("🔮 Сраный оракул")
    markup.add(btn_quote, btn_joke)
    markup.add(btn_oracle)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "Здорова! Я твой личный бот-матерщинник. Зацени обновленного черного оракула на картах! 😈"
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
        
    elif user_text == "🔮 Сраный оракул":
        msg = bot.send_message(
            chat_id, 
            "Так, блядь, закрыл глаза, настроил ментальную связь с космосом и пиши мне любое ЧИСЛО, ща карты раскидаю!", 
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_card_prediction)
        
    else:
        bot.send_chat_action(chat_id, 'typing')
        answer = get_ai_response(chat_id, user_text)
        bot.send_message(chat_id, answer, reply_markup=get_main_keyboard(), parse_mode='Markdown')

def process_card_prediction(message):
    chat_id = message.chat.id
    user_num = message.text
    
    temp_msg = bot.send_message(chat_id, f"Принял число {user_num}... Тасую колоду, сука...")
    bot.send_chat_action(chat_id, 'typing')
    
    random_card = random.choice(TIKTOK_CARDS)
    answer = get_ai_response(chat_id, user_text=user_num, special_mode="oracle_card", chosen_card=random_card, user_number=user_num)
    
    try:
        bot.delete_message(chat_id, temp_msg.message_id)
    except Exception:
        pass
        
    final_text = f"🃏 *Итак, сука, тебе выпала карта: {random_card}!*\n\n{answer}"
    bot.send_message(chat_id, final_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

if __name__ == '__main__':
    server_thread = Thread(target=run_web_server)
    server_thread.start()
    bot.infinity_polling()
